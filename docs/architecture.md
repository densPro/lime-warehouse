# Architecture notes

Decisions made while building, and why. The brief is in `CLAUDE.md`.

## Stock is a ledger plus a cache of its sum

- `stock_movements` is append-only: no endpoint updates or deletes a row.
- `stock_levels` holds the current quantity per (item, bin) so reads are cheap. It is only changed by `InventoryService.move()`, in the same transaction as the ledger row, so the two cannot disagree.
- `move()` uses single conditional `UPDATE` statements instead of read-then-write, which is what stops two concurrent picks from both taking the last units. This works the same on PostgreSQL and SQLite, and does not depend on `SELECT ... FOR UPDATE`.
- DB check constraints are the backstop: `stock_levels.quantity >= 0`, `stock_movements.quantity > 0`, `pick_lines.picked_qty <= quantity`.
- Services own their transactions and commit explicitly. A request that fails is rolled back whole, so a failed receipt line cannot leave half the stock booked.

## Flows

**Receiving:** `goods_receipt` -> `receipt` movement into the `RECV` bin -> purchase-order line `received_qty` and status updated. Expected quantity is what is still outstanding on the order, so a delivery in two parts is not flagged on the second one.

**Put-away:** one `putaway` movement with a from and a to bin.

**Picking:** a pick list is planned against current stock, but nothing is reserved. The real check happens when a pick is confirmed, because stock can change between planning and picking.

**Stock count:** `open` snapshots the bin's system quantities. `submit` requires every item to be counted. `approve` computes the adjustment against the **live** quantity (not the snapshot), so moves made during the count are not undone. Variance shown on the count is counted minus snapshot.

## Decisions to confirm

These were chosen by the builder, not specified:

- Quantities are integers (whole cases/boxes). Weight-based stock would need decimals.
- Items and purchase orders are warehouse copies; the ERP is the master. There is no sync yet.
- No stock reservation between pick-list planning and picking.
- Count approval does not require the approver to differ from the person who opened the count.
- Permissions reuse the existing `stock:*`, `purchase:*` and `product:*` codes in mango-auth's `erp` app instead of adding finer ones.
- `mango_auth_client` is copied into `shared/` rather than installed as a dependency.
