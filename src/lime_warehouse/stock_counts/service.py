import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lime_warehouse.catalog.service import CatalogService
from lime_warehouse.inventory.models import ADJUSTMENT_IN, ADJUSTMENT_OUT, StockLevel
from lime_warehouse.inventory.service import InventoryService
from lime_warehouse.shared.errors import Conflict, Invalid, NotFound
from lime_warehouse.shared.models import utcnow
from lime_warehouse.shared.pagination import PageParams, paginate
from lime_warehouse.stock_counts.models import (
    COUNT_APPROVED,
    COUNT_CANCELLED,
    COUNT_OPEN,
    COUNT_SUBMITTED,
    StockCount,
    StockCountLine,
)

logger = logging.getLogger("lime_warehouse.stock_counts")


class StockCountService:
    """open -> record counts -> submit -> approve. Only approval touches stock, and it writes the ledger."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.catalog = CatalogService(session)
        self.inventory = InventoryService(session)

    async def open(self, actor_id: str, location_id: str) -> StockCount:
        await self.catalog.require_location(location_id, active=True)
        in_flight = await self.session.execute(
            select(StockCount.id).where(
                StockCount.location_id == location_id, StockCount.status.in_([COUNT_OPEN, COUNT_SUBMITTED])
            )
        )
        if existing := in_flight.scalars().first():
            raise Conflict("This location already has an unfinished count", {"stock_count_id": existing})
        levels = (
            await self.session.execute(
                select(StockLevel).where(StockLevel.location_id == location_id, StockLevel.quantity > 0)
            )
        ).scalars()
        count = StockCount(location_id=location_id, opened_by=actor_id)
        for level in levels:
            count.lines.append(StockCountLine(item_id=level.item_id, system_qty=level.quantity))
        self.session.add(count)
        await self.session.commit()
        return count

    async def require(self, count_id: str, *, lock: bool = False) -> StockCount:
        stmt = select(StockCount).where(StockCount.id == count_id)
        if lock:
            stmt = stmt.with_for_update()
        count = (await self.session.execute(stmt)).scalar_one_or_none()
        if count is None:
            raise NotFound(f"Stock count {count_id} not found")
        return count

    async def list_counts(self, params: PageParams, status: str | None, location_id: str | None):
        stmt = select(StockCount).order_by(StockCount.created_at.desc(), StockCount.id)
        if status:
            stmt = stmt.where(StockCount.status == status)
        if location_id:
            stmt = stmt.where(StockCount.location_id == location_id)
        return await paginate(self.session, stmt, params)

    async def record(self, count_id: str, counted: list[tuple[str, int]]) -> StockCount:
        count = await self.require(count_id, lock=True)
        if count.status != COUNT_OPEN:
            raise Conflict(f"Counts can only be recorded while the count is open, this one is {count.status}")
        by_item = {line.item_id: line for line in count.lines}
        for item_id, qty in counted:
            line = by_item.get(item_id)
            if line is None:  # found in the bin but the system had none: variance against 0
                await self.catalog.require_item(item_id, active=True)
                line = StockCountLine(item_id=item_id, system_qty=0)
                count.lines.append(line)
                by_item[item_id] = line
            line.counted_qty = qty
        await self.session.commit()
        return count

    async def submit(self, count_id: str) -> StockCount:
        count = await self.require(count_id, lock=True)
        if count.status != COUNT_OPEN:
            raise Conflict(f"Only an open count can be submitted, this one is {count.status}")
        missing = [line.item_id for line in count.lines if line.counted_qty is None]
        if missing:
            raise Invalid(
                "Every item in the bin must be counted before submitting", {"uncounted_item_ids": missing}
            )
        count.status = COUNT_SUBMITTED
        await self.session.commit()
        return count

    async def approve(self, actor_id: str, count_id: str, reason: str) -> StockCount:
        """Correct the system to the counted quantities, one ledger movement per variance.

        The correction is computed against the live quantity, so moves made while counting are not undone.
        """
        count = await self.require(count_id, lock=True)
        if count.status != COUNT_SUBMITTED:
            raise Conflict(f"Only a submitted count can be approved, this one is {count.status}")
        for line in count.lines:
            current = await self.inventory.quantity_at(line.item_id, count.location_id)
            delta = line.counted_qty - current
            if delta == 0:
                continue
            movement = await self.inventory.move(
                item_id=line.item_id,
                quantity=abs(delta),
                movement_type=ADJUSTMENT_IN if delta > 0 else ADJUSTMENT_OUT,
                actor_id=actor_id,
                reason=reason,
                to_location_id=count.location_id if delta > 0 else None,
                from_location_id=count.location_id if delta < 0 else None,
                reference_type="stock_count",
                reference_id=count.id,
            )
            line.adjustment_movement_id = movement.id
        count.status = COUNT_APPROVED
        count.approved_by = actor_id
        count.approval_reason = reason
        count.approved_at = utcnow()
        await self.session.commit()
        logger.info(
            "stock count approved",
            extra={
                "event": "stock_count_approved",
                "stock_count_id": count.id,
                "actor_id": actor_id,
                "adjustments": sum(1 for line in count.lines if line.adjustment_movement_id),
            },
        )
        return count

    async def cancel(self, actor_id: str, count_id: str) -> StockCount:
        count = await self.require(count_id, lock=True)
        if count.status not in (COUNT_OPEN, COUNT_SUBMITTED):
            raise Conflict(f"This count is already {count.status}")
        count.status = COUNT_CANCELLED
        await self.session.commit()
        logger.info(
            "stock count cancelled",
            extra={"event": "stock_count_cancelled", "stock_count_id": count.id, "actor_id": actor_id},
        )
        return count
