import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lime_warehouse.catalog.service import CatalogService
from lime_warehouse.inventory.models import RECEIPT
from lime_warehouse.inventory.service import InventoryService
from lime_warehouse.receiving.models import (
    OVER,
    PO_OPEN,
    PO_PARTIAL,
    PO_RECEIVED,
    SHORT,
    UNEXPECTED,
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
)
from lime_warehouse.shared.errors import Conflict, Invalid, NotFound
from lime_warehouse.shared.models import new_id
from lime_warehouse.shared.pagination import PageParams, paginate

logger = logging.getLogger("lime_warehouse.receiving")


class ReceivingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.catalog = CatalogService(session)
        self.inventory = InventoryService(session)

    # --- purchase orders -----------------------------------------------------
    async def create_purchase_order(self, po_number: str, supplier: str, lines: list[tuple[str, int]]):
        po_number = po_number.strip().upper()
        if (
            await self.session.execute(select(PurchaseOrder).where(PurchaseOrder.po_number == po_number))
        ).scalar_one_or_none():
            raise Conflict(f"Purchase order {po_number} already exists")
        if len({item_id for item_id, _ in lines}) != len(lines):
            raise Invalid("Each item may appear only once on a purchase order")
        po = PurchaseOrder(po_number=po_number, supplier=supplier)
        for item_id, qty in lines:
            await self.catalog.require_item(item_id, active=True)
            po.lines.append(PurchaseOrderLine(item_id=item_id, ordered_qty=qty))
        self.session.add(po)
        await self.session.commit()
        return po

    async def require_purchase_order(self, po_id: str, *, lock: bool = False) -> PurchaseOrder:
        stmt = select(PurchaseOrder).where(PurchaseOrder.id == po_id)
        if lock:
            stmt = stmt.with_for_update()
        po = (await self.session.execute(stmt)).scalar_one_or_none()
        if po is None:
            raise NotFound(f"Purchase order {po_id} not found")
        return po

    async def list_purchase_orders(self, params: PageParams, status: str | None):
        stmt = select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc(), PurchaseOrder.id)
        if status:
            stmt = stmt.where(PurchaseOrder.status == status)
        return await paginate(self.session, stmt, params)

    # --- goods receipts --------------------------------------------------------
    async def receive(self, actor_id: str, po_id: str | None, notes: str, lines: list[tuple[str, int]]):
        """Book a delivery into the receiving bin and flag every mismatch with the order.

        Goods that are physically there are always recorded (the system must reflect reality);
        differences are flagged on the receipt, never silently corrected.
        """
        receiving = await self.catalog.receiving_location()
        po = await self.require_purchase_order(po_id, lock=True) if po_id else None
        po_lines = {pl.item_id: pl for pl in po.lines} if po else {}

        counted: dict[str, int] = {}
        for item_id, qty in lines:  # the same item counted twice on one delivery is one line
            counted[item_id] = counted.get(item_id, 0) + qty

        receipt = GoodsReceipt(id=new_id(), purchase_order_id=po_id, received_by=actor_id, notes=notes)
        for item_id, qty in counted.items():
            expected: int | None = None
            discrepancy: str | None = UNEXPECTED
            po_line = po_lines.get(item_id)
            if po_line is not None:
                expected = max(po_line.ordered_qty - po_line.received_qty, 0)
                discrepancy = SHORT if qty < expected else OVER if qty > expected else None
                po_line.received_qty += qty
            movement = await self.inventory.move(
                item_id=item_id,
                quantity=qty,
                movement_type=RECEIPT,
                actor_id=actor_id,
                reason=f"Goods receipt{f' for {po.po_number}' if po else ' without a purchase order'}",
                to_location_id=receiving.id,
                reference_type="goods_receipt",
                reference_id=receipt.id,
            )
            receipt.lines.append(
                GoodsReceiptLine(
                    item_id=item_id,
                    expected_qty=expected,
                    received_qty=qty,
                    discrepancy=discrepancy,
                    movement_id=movement.id,
                )
            )
        receipt.has_discrepancy = any(line.discrepancy for line in receipt.lines)

        if po:
            if all(pl.received_qty >= pl.ordered_qty for pl in po.lines):
                po.status = PO_RECEIVED
            elif any(pl.received_qty > 0 for pl in po.lines):
                po.status = PO_PARTIAL
            else:
                po.status = PO_OPEN

        self.session.add(receipt)
        await self.session.commit()
        logger.log(
            logging.WARNING if receipt.has_discrepancy else logging.INFO,
            "goods receipt booked",
            extra={
                "event": "goods_receipt",
                "receipt_id": receipt.id,
                "purchase_order_id": po_id,
                "has_discrepancy": receipt.has_discrepancy,
                "actor_id": actor_id,
            },
        )
        return receipt

    async def require_receipt(self, receipt_id: str) -> GoodsReceipt:
        receipt = await self.session.get(GoodsReceipt, receipt_id)
        if receipt is None:
            raise NotFound(f"Goods receipt {receipt_id} not found")
        return receipt

    async def list_receipts(self, params: PageParams, po_id: str | None, has_discrepancy: bool | None):
        stmt = select(GoodsReceipt).order_by(GoodsReceipt.created_at.desc(), GoodsReceipt.id)
        if po_id:
            stmt = stmt.where(GoodsReceipt.purchase_order_id == po_id)
        if has_discrepancy is not None:
            stmt = stmt.where(GoodsReceipt.has_discrepancy == has_discrepancy)
        return await paginate(self.session, stmt, params)
