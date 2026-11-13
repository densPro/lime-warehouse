from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lime_warehouse.shared.models import Base, new_id, utcnow

PO_OPEN = "open"
PO_PARTIAL = "partially_received"
PO_RECEIVED = "received"

# Why a receipt line does not match the purchase order
SHORT = "short"  # fewer than still expected
OVER = "over"  # more than still expected
UNEXPECTED = "unexpected"  # item not on the order, or no order recorded at all


class PurchaseOrder(Base):
    """Warehouse copy of an ERP purchase order: what is expected to arrive."""

    __tablename__ = "purchase_orders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    po_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    supplier: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(32), default=PO_OPEN, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="PurchaseOrderLine.id"
    )


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"
    __table_args__ = (
        UniqueConstraint("purchase_order_id", "item_id"),
        CheckConstraint("ordered_qty > 0", name="ck_po_lines_ordered_positive"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    purchase_order_id: Mapped[str] = mapped_column(ForeignKey("purchase_orders.id"), index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"))
    ordered_qty: Mapped[int] = mapped_column(Integer)
    received_qty: Mapped[int] = mapped_column(Integer, default=0)


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    purchase_order_id: Mapped[str | None] = mapped_column(
        ForeignKey("purchase_orders.id"), nullable=True, index=True
    )
    received_by: Mapped[str] = mapped_column(String(64), index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    has_discrepancy: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    lines: Mapped[list["GoodsReceiptLine"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="GoodsReceiptLine.id"
    )


class GoodsReceiptLine(Base):
    __tablename__ = "goods_receipt_lines"
    __table_args__ = (CheckConstraint("received_qty > 0", name="ck_receipt_lines_received_positive"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    receipt_id: Mapped[str] = mapped_column(ForeignKey("goods_receipts.id"), index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"))
    expected_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    received_qty: Mapped[int] = mapped_column(Integer)
    discrepancy: Mapped[str | None] = mapped_column(String(16), nullable=True)
    movement_id: Mapped[str] = mapped_column(String(32))
