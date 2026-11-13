from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PurchaseOrderLineIn(BaseModel):
    item_id: str
    ordered_qty: int = Field(gt=0)


class PurchaseOrderCreate(BaseModel):
    po_number: str = Field(min_length=1, max_length=64)
    supplier: str = Field(default="", max_length=200)
    lines: list[PurchaseOrderLineIn] = Field(min_length=1)


class PurchaseOrderLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_id: str
    ordered_qty: int
    received_qty: int


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    po_number: str
    supplier: str
    status: str
    created_at: datetime
    lines: list[PurchaseOrderLineOut]


class ReceiptLineIn(BaseModel):
    item_id: str
    received_qty: int = Field(gt=0, description="What was physically counted at the dock")


class GoodsReceiptCreate(BaseModel):
    purchase_order_id: str | None = Field(
        default=None, description="Omit when the delivery has no recorded order; it is flagged as unexpected"
    )
    notes: str = Field(default="", max_length=2000)
    lines: list[ReceiptLineIn] = Field(min_length=1)


class GoodsReceiptLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_id: str
    expected_qty: int | None
    received_qty: int
    discrepancy: str | None
    movement_id: str


class GoodsReceiptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    purchase_order_id: str | None
    received_by: str
    notes: str
    has_discrepancy: bool
    created_at: datetime
    lines: list[GoodsReceiptLineOut]
