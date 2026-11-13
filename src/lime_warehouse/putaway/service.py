from sqlalchemy.ext.asyncio import AsyncSession

from lime_warehouse.inventory.models import PUTAWAY, StockMovement
from lime_warehouse.inventory.service import InventoryService


class PutawayService:
    """Move stock from one bin to another (typically receiving dock to a storage bin).

    The source loses and the destination gains in one transaction, so the system never shows
    the stock in the old bin after it has been moved.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.inventory = InventoryService(session)

    async def put_away(
        self,
        actor_id: str,
        item_id: str,
        from_location_id: str,
        to_location_id: str,
        quantity: int,
        reason: str,
    ) -> StockMovement:
        movement = await self.inventory.move(
            item_id=item_id,
            quantity=quantity,
            movement_type=PUTAWAY,
            actor_id=actor_id,
            reason=reason or "Put-away",
            from_location_id=from_location_id,
            to_location_id=to_location_id,
        )
        await self.session.commit()
        return movement
