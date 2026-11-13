from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from lime_warehouse.shared.models import Base, new_id, utcnow

# movement types
OPENING_BALANCE = "opening_balance"
RECEIPT = "receipt"
PUTAWAY = "putaway"
PICK = "pick"
ADJUSTMENT_IN = "adjustment_in"
ADJUSTMENT_OUT = "adjustment_out"


class StockLevel(Base):
    """Current quantity of one item in one location. Only InventoryService.move() changes it."""

    __tablename__ = "stock_levels"
    __table_args__ = (
        UniqueConstraint("item_id", "location_id"),
        CheckConstraint("quantity >= 0", name="ck_stock_levels_quantity_non_negative"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"), index=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class StockMovement(Base):
    """Append-only ledger. Every change to stock_levels has exactly one row here: who, when, why."""

    __tablename__ = "stock_movements"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_stock_movements_quantity_positive"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"), index=True)
    from_location_id: Mapped[str | None] = mapped_column(
        ForeignKey("locations.id"), nullable=True, index=True
    )
    to_location_id: Mapped[str | None] = mapped_column(
        ForeignKey("locations.id"), nullable=True, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    movement_type: Mapped[str] = mapped_column(String(32), index=True)
    reason: Mapped[str] = mapped_column(String(500), default="")
    reference_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    actor_id: Mapped[str] = mapped_column(String(64), index=True)  # mango-auth user id (token `sub`)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
