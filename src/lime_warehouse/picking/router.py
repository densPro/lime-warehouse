from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from lime_warehouse.picking.schemas import PickConfirm, PickListCreate, PickListOut
from lime_warehouse.picking.service import PickingService
from lime_warehouse.shared.auth import Principal, require
from lime_warehouse.shared.db import get_session
from lime_warehouse.shared.pagination import Page, PageParams, page_of, page_params

router = APIRouter(prefix="/api/v1", tags=["picking"])


def _svc(session: AsyncSession = Depends(get_session)) -> PickingService:
    return PickingService(session)


@router.post("/pick-lists", response_model=PickListOut, status_code=201)
async def create_pick_list(
    body: PickListCreate,
    response: Response,
    user: Principal = require("stock:transfer"),
    svc: PickingService = Depends(_svc),
):
    pick_list = await svc.create(user.sub, body.reference, [(ln.item_id, ln.location_id, ln.quantity) for ln in body.lines])
    response.headers["Location"] = f"/api/v1/pick-lists/{pick_list.id}"
    return pick_list


@router.get("/pick-lists", response_model=Page[PickListOut], dependencies=[require("stock:view")])
async def list_pick_lists(
    status: str | None = None,
    reference: str | None = None,
    params: PageParams = Depends(page_params),
    svc: PickingService = Depends(_svc),
):
    rows, total = await svc.list_pick_lists(params, status, reference)
    return page_of(PickListOut, rows, total, params)


@router.get("/pick-lists/{pick_list_id}", response_model=PickListOut, dependencies=[require("stock:view")])
async def get_pick_list(pick_list_id: str, svc: PickingService = Depends(_svc)):
    return await svc.require(pick_list_id)


@router.post("/pick-lists/{pick_list_id}/lines/{line_id}/picks", response_model=PickListOut)
async def pick_line(
    pick_list_id: str,
    line_id: str,
    body: PickConfirm | None = None,
    user: Principal = require("stock:transfer"),
    svc: PickingService = Depends(_svc),
):
    """Confirm a physical pick. Fails with 409 `insufficient_stock` if the bin does not hold the quantity."""
    return await svc.pick(user.sub, pick_list_id, line_id, body.quantity if body else None)


@router.post("/pick-lists/{pick_list_id}/cancellation", response_model=PickListOut)
async def cancel_pick_list(
    pick_list_id: str, user: Principal = require("stock:transfer"), svc: PickingService = Depends(_svc)
):
    return await svc.cancel(user.sub, pick_list_id)
