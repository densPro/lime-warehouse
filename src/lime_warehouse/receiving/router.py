from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from lime_warehouse.receiving.schemas import (
    GoodsReceiptCreate,
    GoodsReceiptOut,
    PurchaseOrderCreate,
    PurchaseOrderOut,
)
from lime_warehouse.receiving.service import ReceivingService
from lime_warehouse.shared.auth import Principal, require
from lime_warehouse.shared.db import get_session
from lime_warehouse.shared.pagination import Page, PageParams, page_of, page_params

router = APIRouter(prefix="/api/v1", tags=["receiving"])


def _svc(session: AsyncSession = Depends(get_session)) -> ReceivingService:
    return ReceivingService(session)


@router.post(
    "/purchase-orders",
    response_model=PurchaseOrderOut,
    status_code=201,
    dependencies=[require("purchase:create")],
)
async def create_purchase_order(body: PurchaseOrderCreate, response: Response, svc: ReceivingService = Depends(_svc)):
    po = await svc.create_purchase_order(body.po_number, body.supplier, [(ln.item_id, ln.ordered_qty) for ln in body.lines])
    response.headers["Location"] = f"/api/v1/purchase-orders/{po.id}"
    return po


@router.get("/purchase-orders", response_model=Page[PurchaseOrderOut], dependencies=[require("purchase:view")])
async def list_purchase_orders(
    status: str | None = None,
    params: PageParams = Depends(page_params),
    svc: ReceivingService = Depends(_svc),
):
    rows, total = await svc.list_purchase_orders(params, status)
    return page_of(PurchaseOrderOut, rows, total, params)


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderOut, dependencies=[require("purchase:view")])
async def get_purchase_order(po_id: str, svc: ReceivingService = Depends(_svc)):
    return await svc.require_purchase_order(po_id)


@router.post("/goods-receipts", response_model=GoodsReceiptOut, status_code=201)
async def create_goods_receipt(
    body: GoodsReceiptCreate,
    response: Response,
    user: Principal = require("stock:transfer"),
    svc: ReceivingService = Depends(_svc),
):
    """Book a delivery. Mismatches with the order come back flagged on the receipt, not as errors."""
    receipt = await svc.receive(user.sub, body.purchase_order_id, body.notes, [(ln.item_id, ln.received_qty) for ln in body.lines])
    response.headers["Location"] = f"/api/v1/goods-receipts/{receipt.id}"
    return receipt


@router.get("/goods-receipts", response_model=Page[GoodsReceiptOut], dependencies=[require("stock:view")])
async def list_goods_receipts(
    purchase_order_id: str | None = None,
    has_discrepancy: bool | None = None,
    params: PageParams = Depends(page_params),
    svc: ReceivingService = Depends(_svc),
):
    rows, total = await svc.list_receipts(params, purchase_order_id, has_discrepancy)
    return page_of(GoodsReceiptOut, rows, total, params)


@router.get("/goods-receipts/{receipt_id}", response_model=GoodsReceiptOut, dependencies=[require("stock:view")])
async def get_goods_receipt(receipt_id: str, svc: ReceivingService = Depends(_svc)):
    return await svc.require_receipt(receipt_id)
