from conftest import make_item, make_location, receive, recv_id, stock_at


async def make_po(client, lines, number="PO-1"):
    r = await client.post(
        "/api/v1/purchase-orders",
        json={"po_number": number, "supplier": "Tropico", "lines": [{"item_id": i, "ordered_qty": q} for i, q in lines]},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_exact_receipt_has_no_discrepancy_and_lands_in_receiving(client):
    item = await make_item(client)
    po = await make_po(client, [(item, 100)])
    receipt = await receive(client, item, 100, po)
    assert receipt["has_discrepancy"] is False
    assert receipt["lines"][0]["expected_qty"] == 100
    assert await stock_at(client, item, await recv_id(client)) == 100
    assert (await client.get(f"/api/v1/purchase-orders/{po}")).json()["status"] == "received"


async def test_short_delivery_is_flagged_and_order_stays_partial(client):
    item = await make_item(client)
    po = await make_po(client, [(item, 100)])
    receipt = await receive(client, item, 80, po)
    assert receipt["has_discrepancy"] is True
    assert receipt["lines"][0]["discrepancy"] == "short"
    assert (await client.get(f"/api/v1/purchase-orders/{po}")).json()["status"] == "partially_received"
    # the rest arrives later: expected is what is still outstanding
    second = await receive(client, item, 20, po)
    assert second["lines"][0]["expected_qty"] == 20 and second["has_discrepancy"] is False


async def test_over_delivery_is_flagged_and_still_booked(client):
    item = await make_item(client)
    po = await make_po(client, [(item, 10)])
    receipt = await receive(client, item, 15, po)
    assert receipt["lines"][0]["discrepancy"] == "over"
    assert await stock_at(client, item, await recv_id(client)) == 15


async def test_receipt_without_order_is_unexpected(client):
    item = await make_item(client)
    receipt = await receive(client, item, 7)
    assert receipt["has_discrepancy"] is True
    assert receipt["lines"][0]["discrepancy"] == "unexpected" and receipt["lines"][0]["expected_qty"] is None
    flagged = (await client.get("/api/v1/goods-receipts", params={"has_discrepancy": True})).json()
    assert flagged["total"] == 1


async def test_item_not_on_order_is_unexpected(client):
    ordered, other = await make_item(client, "A"), await make_item(client, "B")
    po = await make_po(client, [(ordered, 5)])
    receipt = await receive(client, other, 3, po)
    assert receipt["lines"][0]["discrepancy"] == "unexpected"


async def test_receipt_records_who_and_why_in_the_ledger(client):
    item = await make_item(client)
    await receive(client, item, 4)
    moves = (await client.get("/api/v1/stock-movements", params={"item_id": item})).json()["items"]
    assert len(moves) == 1
    assert moves[0]["movement_type"] == "receipt" and moves[0]["actor_id"] == "u-clerk"
    assert moves[0]["reason"] and moves[0]["reference_type"] == "goods_receipt"


async def test_unknown_item_or_order_is_404_and_changes_nothing(client):
    item = await make_item(client)
    r = await client.post("/api/v1/goods-receipts", json={"purchase_order_id": "nope", "lines": [{"item_id": item, "received_qty": 1}]})
    assert r.status_code == 404
    assert await stock_at(client, item, await recv_id(client)) == 0


async def test_duplicate_po_number_is_conflict(client):
    item = await make_item(client)
    await make_po(client, [(item, 1)], "PO-X")
    r = await client.post("/api/v1/purchase-orders", json={"po_number": "po-x", "lines": [{"item_id": item, "ordered_qty": 1}]})
    assert r.status_code == 409


async def test_receiving_needs_transfer_permission(client):
    item = await make_item(client)
    from conftest import as_user

    r = await client.post(
        "/api/v1/goods-receipts",
        json={"lines": [{"item_id": item, "received_qty": 1}]},
        headers=as_user("viewer", ["stock:view"]),
    )
    assert r.status_code == 403
    await make_location(client)  # keep helper import used
