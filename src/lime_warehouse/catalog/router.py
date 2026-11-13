from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from lime_warehouse.catalog.schemas import (
    ItemCreate,
    ItemOut,
    ItemUpdate,
    LocationCreate,
    LocationOut,
    LocationUpdate,
)
from lime_warehouse.catalog.service import CatalogService
from lime_warehouse.shared.auth import require
from lime_warehouse.shared.db import get_session
from lime_warehouse.shared.pagination import Page, PageParams, page_of, page_params

router = APIRouter(prefix="/api/v1", tags=["catalog"])


def _svc(session: AsyncSession = Depends(get_session)) -> CatalogService:
    return CatalogService(session)


# --- items -----------------------------------------------------------------
@router.post("/items", response_model=ItemOut, status_code=201, dependencies=[require("product:create")])
async def create_item(body: ItemCreate, response: Response, svc: CatalogService = Depends(_svc)):
    item = await svc.create_item(body.sku, body.name, body.unit)
    response.headers["Location"] = f"/api/v1/items/{item.id}"
    return item


@router.get("/items", response_model=Page[ItemOut], dependencies=[require("stock:view")])
async def list_items(
    q: str | None = Query(None, description="Match on SKU or name"),
    active: bool | None = None,
    params: PageParams = Depends(page_params),
    svc: CatalogService = Depends(_svc),
):
    rows, total = await svc.list_items(params, q, active)
    return page_of(ItemOut, rows, total, params)


@router.get("/items/{item_id}", response_model=ItemOut, dependencies=[require("stock:view")])
async def get_item(item_id: str, svc: CatalogService = Depends(_svc)):
    return await svc.require_item(item_id)


@router.patch("/items/{item_id}", response_model=ItemOut, dependencies=[require("product:edit")])
async def update_item(item_id: str, body: ItemUpdate, svc: CatalogService = Depends(_svc)):
    return await svc.update_item(item_id, **body.model_dump(exclude_unset=True))


# --- locations ---------------------------------------------------------------
@router.post("/locations", response_model=LocationOut, status_code=201, dependencies=[require("stock:adjust")])
async def create_location(body: LocationCreate, response: Response, svc: CatalogService = Depends(_svc)):
    location = await svc.create_location(body.code, body.zone, body.kind)
    response.headers["Location"] = f"/api/v1/locations/{location.id}"
    return location


@router.get("/locations", response_model=Page[LocationOut], dependencies=[require("stock:view")])
async def list_locations(
    zone: str | None = None,
    active: bool | None = None,
    params: PageParams = Depends(page_params),
    svc: CatalogService = Depends(_svc),
):
    rows, total = await svc.list_locations(params, zone, active)
    return page_of(LocationOut, rows, total, params)


@router.get("/locations/{location_id}", response_model=LocationOut, dependencies=[require("stock:view")])
async def get_location(location_id: str, svc: CatalogService = Depends(_svc)):
    return await svc.require_location(location_id)


@router.patch("/locations/{location_id}", response_model=LocationOut, dependencies=[require("stock:adjust")])
async def update_location(location_id: str, body: LocationUpdate, svc: CatalogService = Depends(_svc)):
    return await svc.update_location(location_id, **body.model_dump(exclude_unset=True))
