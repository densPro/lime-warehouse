from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from lime_warehouse.shared.models import Base, new_id, utcnow

RECEIVING = "receiving"  # staging bin where delivered goods land before put-away
STORAGE = "storage"


class Item(Base):
    """A stockable product. Product master data is owned by the ERP; this is the warehouse copy."""

    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str] = mapped_column(String(16), default="case")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Location(Base):
    """A bin (or the receiving dock). Stock always sits in exactly one location per row of stock_levels."""

    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    zone: Mapped[str] = mapped_column(String(32), default="")
    kind: Mapped[str] = mapped_column(String(16), default=STORAGE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
