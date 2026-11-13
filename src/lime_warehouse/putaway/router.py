from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from lime_warehouse.inventory.schemas import StockMovementOut
from lime_warehouse.putaway.schemas import PutawayCreate
from lime_warehouse.putaway.service import PutawayService
from lime_warehouse.shared.auth import Principal, require
from lime_warehouse.shared.db import get_session

router = APIRouter(prefix="/api/v1", tags=["putaway"])


@router.post("/putaways", response_model=StockMovementOut, status_code=201)
async def create_putaway(
    body: PutawayCreate,
    response: Response,
    user: Principal = require("stock:transfer"),
    session: AsyncSession = Depends(get_session),
):
    """Record a physical move between bins. Fails with 409 `insufficient_stock` if the source bin lacks the quantity."""
    movement = await PutawayService(session).put_away(
        user.sub, body.item_id, body.from_location_id, body.to_location_id, body.quantity, body.reason
    )
    response.headers["Location"] = f"/api/v1/stock-movements?reference_id={movement.id}"
    return movement
