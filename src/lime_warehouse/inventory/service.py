import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from lime_warehouse.catalog.service import CatalogService
from lime_warehouse.inventory.models import StockLevel, StockMovement
from lime_warehouse.shared.errors import InsufficientStock, Invalid
from lime_warehouse.shared.logging import request_id_var
from lime_warehouse.shared.pagination import PageParams, paginate

logger = logging.getLogger("lime_warehouse.inventory")


class InventoryService:
    """The only writer of stock. Other domains call move(); nobody edits a quantity directly."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.catalog = CatalogService(session)

    async def move(
        self,
        *,
        item_id: str,
        quantity: int,
        movement_type: str,
        actor_id: str,
        reason: str = "",
        from_location_id: str | None = None,
        to_location_id: str | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
    ) -> StockMovement:
        """Change stock and write the ledger row in the caller's transaction. The caller commits.

        `from` only: stock leaves. `to` only: stock arrives. Both: stock moves between bins.
        """
        if quantity <= 0:
            raise Invalid("Quantity must be greater than zero")
        if from_location_id is None and to_location_id is None:
            raise Invalid("A movement needs a from or a to location")
        if from_location_id == to_location_id:
            raise Invalid("From and to locations must differ")

        await self.catalog.require_item(item_id, active=True)
        if from_location_id:
            await self.catalog.require_location(from_location_id)
        if to_location_id:
            await self.catalog.require_location(to_location_id, active=True)

        # Single conditional UPDATEs: the check and the change are one atomic statement, so two
        # concurrent requests can never both take the last units (no read-then-write race).
        if from_location_id:
            taken = await self.session.execute(
                update(StockLevel)
                .where(
                    StockLevel.item_id == item_id,
                    StockLevel.location_id == from_location_id,
                    StockLevel.quantity >= quantity,
                )
                .values(quantity=StockLevel.quantity - quantity)
                .execution_options(synchronize_session=False)
            )
            if taken.rowcount == 0:
                available = await self.quantity_at(item_id, from_location_id)
                raise InsufficientStock(
                    f"Location holds {available} of this item, {quantity} requested",
                    {"item_id": item_id, "location_id": from_location_id, "available": available},
                )
        if to_location_id:
            added = await self.session.execute(
                update(StockLevel)
                .where(StockLevel.item_id == item_id, StockLevel.location_id == to_location_id)
                .values(quantity=StockLevel.quantity + quantity)
                .execution_options(synchronize_session=False)
            )
            if added.rowcount == 0:  # first stock of this item in this bin
                self.session.add(StockLevel(item_id=item_id, location_id=to_location_id, quantity=quantity))

        movement = StockMovement(
            item_id=item_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            quantity=quantity,
            movement_type=movement_type,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            actor_id=actor_id,
            request_id=request_id_var.get(),
        )
        self.session.add(movement)
        await self.session.flush()
        logger.info(
            "stock movement",
            extra={
                "event": "stock_movement",
                "movement_id": movement.id,
                "movement_type": movement_type,
                "item_id": item_id,
                "quantity": quantity,
                "from_location_id": from_location_id,
                "to_location_id": to_location_id,
                "actor_id": actor_id,
                "reference_type": reference_type,
                "reference_id": reference_id,
            },
        )
        return movement

    async def quantity_at(self, item_id: str, location_id: str) -> int:
        level = await self._level(item_id, location_id)
        return level.quantity if level else 0

    async def _level(self, item_id: str, location_id: str) -> StockLevel | None:
        stmt = select(StockLevel).where(StockLevel.item_id == item_id, StockLevel.location_id == location_id)
        # The UPDATEs above bypass the identity map, so always re-read the row.
        result = await self.session.execute(stmt.execution_options(populate_existing=True))
        return result.scalar_one_or_none()

    async def list_levels(
        self, params: PageParams, item_id: str | None, location_id: str | None, include_empty: bool
    ):
        stmt = select(StockLevel).order_by(StockLevel.location_id, StockLevel.item_id)
        if item_id:
            stmt = stmt.where(StockLevel.item_id == item_id)
        if location_id:
            stmt = stmt.where(StockLevel.location_id == location_id)
        if not include_empty:
            stmt = stmt.where(StockLevel.quantity > 0)
        return await paginate(self.session, stmt, params)

    async def list_movements(
        self,
        params: PageParams,
        item_id: str | None,
        location_id: str | None,
        movement_type: str | None,
        actor_id: str | None,
    ):
        stmt = select(StockMovement).order_by(StockMovement.created_at.desc(), StockMovement.id)
        if item_id:
            stmt = stmt.where(StockMovement.item_id == item_id)
        if location_id:
            stmt = stmt.where(
                (StockMovement.from_location_id == location_id)
                | (StockMovement.to_location_id == location_id)
            )
        if movement_type:
            stmt = stmt.where(StockMovement.movement_type == movement_type)
        if actor_id:
            stmt = stmt.where(StockMovement.actor_id == actor_id)
        return await paginate(self.session, stmt, params)
