"""Imports every domain's models so Base.metadata is complete (used by Alembic and create_all)."""

from lime_warehouse.catalog.models import Item, Location
from lime_warehouse.inventory.models import StockLevel, StockMovement
from lime_warehouse.picking.models import PickLine, PickList
from lime_warehouse.receiving.models import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine
from lime_warehouse.shared.models import Base
from lime_warehouse.stock_counts.models import StockCount, StockCountLine

__all__ = [
    "Base",
    "GoodsReceipt",
    "GoodsReceiptLine",
    "Item",
    "Location",
    "PickLine",
    "PickList",
    "PurchaseOrder",
    "PurchaseOrderLine",
    "StockCount",
    "StockCountLine",
    "StockLevel",
    "StockMovement",
]
