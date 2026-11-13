from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from lime_warehouse.shared.auth import Principal, require
from lime_warehouse.shared.db import get_session
from lime_warehouse.shared.pagination import Page, PageParams, page_of, page_params
from lime_warehouse.stock_counts.schemas import ApproveCount, CountedLines, StockCountCreate, StockCountOut
from lime_warehouse.stock_counts.service import StockCountService

router = APIRouter(prefix="/api/v1", tags=["stock-counts"])


def _svc(session: AsyncSession = Depends(get_session)) -> StockCountService:
    return StockCountService(session)


@router.post("/stock-counts", response_model=StockCountOut, status_code=201)
async def open_stock_count(
    body: StockCountCreate,
    response: Response,
    user: Principal = require("stock:transfer"),
    svc: StockCountService = Depends(_svc),
):
    """Start counting one bin. The system quantities are snapshotted as the baseline for variances."""
    count = await svc.open(user.sub, body.location_id)
    response.headers["Location"] = f"/api/v1/stock-counts/{count.id}"
    return count


@router.get("/stock-counts", response_model=Page[StockCountOut], dependencies=[require("stock:view")])
async def list_stock_counts(
    status: str | None = None,
    location_id: str | None = None,
    params: PageParams = Depends(page_params),
    svc: StockCountService = Depends(_svc),
):
    rows, total = await svc.list_counts(params, status, location_id)
    return page_of(StockCountOut, rows, total, params)


@router.get("/stock-counts/{count_id}", response_model=StockCountOut, dependencies=[require("stock:view")])
async def get_stock_count(count_id: str, svc: StockCountService = Depends(_svc)):
    return await svc.require(count_id)


@router.put(
    "/stock-counts/{count_id}/lines", response_model=StockCountOut, dependencies=[require("stock:transfer")]
)
async def record_counted_lines(count_id: str, body: CountedLines, svc: StockCountService = Depends(_svc)):
    """Record (or re-record) counted quantities. An item not in the baseline is added with system quantity 0."""
    return await svc.record(count_id, [(ln.item_id, ln.counted_qty) for ln in body.lines])


@router.post("/stock-counts/{count_id}/submission", response_model=StockCountOut, dependencies=[require("stock:transfer")])
async def submit_stock_count(count_id: str, svc: StockCountService = Depends(_svc)):
    return await svc.submit(count_id)


@router.post("/stock-counts/{count_id}/approval", response_model=StockCountOut)
async def approve_stock_count(
    count_id: str,
    body: ApproveCount,
    user: Principal = require("stock:adjust"),
    svc: StockCountService = Depends(_svc),
):
    """Apply the variances to stock. Needs `stock:adjust`; the reason is stored on every adjustment movement."""
    return await svc.approve(user.sub, count_id, body.reason)


@router.post("/stock-counts/{count_id}/cancellation", response_model=StockCountOut)
async def cancel_stock_count(
    count_id: str, user: Principal = require("stock:transfer"), svc: StockCountService = Depends(_svc)
):
    return await svc.cancel(user.sub, count_id)
