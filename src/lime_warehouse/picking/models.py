from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lime_warehouse.shared.models import Base, new_id, utcnow

PICK_OPEN = "open"
PICK_IN_PROGRESS = "in_progress"
PICK_COMPLETED = "completed"
PICK_CANCELLED = "cancelled"


class PickList(Base):
    __tablename__ = "pick_lists"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    reference: Mapped[str] = mapped_column(String(64), default="", index=True)  # e.g. the sales order number
    status: Mapped[str] = mapped_column(String(16), default=PICK_OPEN, index=True)
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    lines: Mapped[list["PickLine"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="PickLine.id"
    )


class PickLine(Base):
    """Take `quantity` of an item from one specific bin."""

    __tablename__ = "pick_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_pick_lines_quantity_positive"),
        CheckConstraint("picked_qty >= 0 AND picked_qty <= quantity", name="ck_pick_lines_picked_in_range"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    pick_list_id: Mapped[str] = mapped_column(ForeignKey("pick_lists.id"), index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"))
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    picked_qty: Mapped[int] = mapped_column(Integer, default=0)
