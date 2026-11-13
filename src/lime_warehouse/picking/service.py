import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lime_warehouse.catalog.service import CatalogService
from lime_warehouse.inventory.models import PICK
from lime_warehouse.inventory.service import InventoryService
from lime_warehouse.picking.models import (
    PICK_CANCELLED,
    PICK_COMPLETED,
    PICK_IN_PROGRESS,
    PICK_OPEN,
    PickLine,
    PickList,
)
from lime_warehouse.shared.errors import Conflict, InsufficientStock, Invalid, NotFound
from lime_warehouse.shared.pagination import PageParams, paginate

logger = logging.getLogger("lime_warehouse.picking")


class PickingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.catalog = CatalogService(session)
        self.inventory = InventoryService(session)

    async def create(self, actor_id: str, reference: str, lines: list[tuple[str, str, int]]) -> PickList:
        """Plan a pick. Every line must be satisfiable from its bin right now (checked again at pick time)."""
        wanted: dict[tuple[str, str], int] = {}
        for item_id, location_id, qty in lines:
            await self.catalog.require_item(item_id, active=True)
            await self.catalog.require_location(location_id, active=True)
            wanted[(item_id, location_id)] = wanted.get((item_id, location_id), 0) + qty
        for (item_id, location_id), qty in wanted.items():
            available = await self.inventory.quantity_at(item_id, location_id)
            if available < qty:
                raise InsufficientStock(
                    f"Location holds {available} of this item, {qty} requested",
                    {"item_id": item_id, "location_id": location_id, "available": available},
                )
        pick_list = PickList(reference=reference, created_by=actor_id)
        for item_id, location_id, qty in lines:
            pick_list.lines.append(PickLine(item_id=item_id, location_id=location_id, quantity=qty))
        self.session.add(pick_list)
        await self.session.commit()
        return pick_list

    async def require(self, pick_list_id: str) -> PickList:
        pick_list = await self.session.get(PickList, pick_list_id)
        if pick_list is None:
            raise NotFound(f"Pick list {pick_list_id} not found")
        return pick_list

    async def list_pick_lists(self, params: PageParams, status: str | None, reference: str | None):
        stmt = select(PickList).order_by(PickList.created_at.desc(), PickList.id)
        if status:
            stmt = stmt.where(PickList.status == status)
        if reference:
            stmt = stmt.where(PickList.reference == reference)
        return await paginate(self.session, stmt, params)

    async def pick(self, actor_id: str, pick_list_id: str, line_id: str, quantity: int | None) -> PickList:
        pick_list = await self.require(pick_list_id)
        if pick_list.status in (PICK_COMPLETED, PICK_CANCELLED):
            raise Conflict(f"Pick list is {pick_list.status}")
        # Lock the line so two pickers cannot both take the same remaining quantity.
        line = (
            await self.session.execute(
                select(PickLine)
                .where(PickLine.id == line_id, PickLine.pick_list_id == pick_list_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if line is None:
            raise NotFound(f"Line {line_id} not found on this pick list")
        remaining = line.quantity - line.picked_qty
        qty = remaining if quantity is None else quantity
        if remaining == 0:
            raise Conflict("This line is already fully picked")
        if qty > remaining:
            raise Invalid(f"Only {remaining} left to pick on this line, {qty} requested")

        await self.inventory.move(
            item_id=line.item_id,
            quantity=qty,
            movement_type=PICK,
            actor_id=actor_id,
            reason=f"Pick for {pick_list.reference or pick_list.id}",
            from_location_id=line.location_id,
            reference_type="pick_list",
            reference_id=pick_list.id,
        )
        line.picked_qty += qty
        pick_list.status = (
            PICK_COMPLETED
            if all(pl.picked_qty == pl.quantity for pl in pick_list.lines)
            else PICK_IN_PROGRESS
        )
        await self.session.commit()
        return pick_list

    async def cancel(self, actor_id: str, pick_list_id: str) -> PickList:
        pick_list = await self.require(pick_list_id)
        if pick_list.status != PICK_OPEN:
            raise Conflict(f"Only an open pick list can be cancelled, this one is {pick_list.status}")
        pick_list.status = PICK_CANCELLED
        await self.session.commit()
        logger.info(
            "pick list cancelled",
            extra={"event": "pick_list_cancelled", "pick_list_id": pick_list.id, "actor_id": actor_id},
        )
        return pick_list
