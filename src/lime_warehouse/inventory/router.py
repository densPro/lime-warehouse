from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from lime_warehouse.inventory.schemas import StockLevelOut, StockMovementOut
from lime_warehouse.inventory.service import InventoryService
from lime_warehouse.shared.auth import require
from lime_warehouse.shared.db import get_session
from lime_warehouse.shared.pagination import Page, PageParams, page_of, page_params

router = APIRouter(prefix="/api/v1", tags=["inventory"], dependencies=[require("stock:view")])


def _svc(session: AsyncSession = Depends(get_session)) -> InventoryService:
    return InventoryService(session)


@router.get("/stock-levels", response_model=Page[StockLevelOut])
async def list_stock_levels(
    item_id: str | None = None,
    location_id: str | None = None,
    include_empty: bool = False,
    params: PageParams = Depends(page_params),
    svc: InventoryService = Depends(_svc),
):
    rows, total = await svc.list_levels(params, item_id, location_id, include_empty)
    return page_of(StockLevelOut, rows, total, params)


@router.get("/stock-movements", response_model=Page[StockMovementOut])
async def list_stock_movements(
    item_id: str | None = None,
    location_id: str | None = None,
    movement_type: str | None = None,
    actor_id: str | None = None,
    params: PageParams = Depends(page_params),
    svc: InventoryService = Depends(_svc),
):
    """The audit trail: every change to stock, newest first."""
    rows, total = await svc.list_movements(params, item_id, location_id, movement_type, actor_id)
    return page_of(StockMovementOut, rows, total, params)
