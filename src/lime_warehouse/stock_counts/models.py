from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lime_warehouse.shared.models import Base, new_id, utcnow

COUNT_OPEN = "open"
COUNT_SUBMITTED = "submitted"
COUNT_APPROVED = "approved"
COUNT_CANCELLED = "cancelled"


class StockCount(Base):
    """A physical count of one bin. Nothing changes in stock until a second step approves it."""

    __tablename__ = "stock_counts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default=COUNT_OPEN, index=True)
    opened_by: Mapped[str] = mapped_column(String(64))
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approval_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lines: Mapped[list["StockCountLine"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="StockCountLine.id"
    )


class StockCountLine(Base):
    __tablename__ = "stock_count_lines"
    __table_args__ = (
        UniqueConstraint("stock_count_id", "item_id"),
        CheckConstraint(
            "counted_qty IS NULL OR counted_qty >= 0", name="ck_count_lines_counted_non_negative"
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    stock_count_id: Mapped[str] = mapped_column(ForeignKey("stock_counts.id"), index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"))
    system_qty: Mapped[int] = mapped_column(Integer)  # snapshot when the count was opened
    counted_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    adjustment_movement_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
