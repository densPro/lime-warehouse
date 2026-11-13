from conftest import as_user, make_item, make_location, receive, recv_id, stock_at


async def stocked_bin(client, qty=10):
    item = await make_item(client)
    bin_id = await make_location(client)
    await receive(client, item, qty)
    await client.post(
        "/api/v1/putaways",
        json={"item_id": item, "from_location_id": await recv_id(client), "to_location_id": bin_id, "quantity": qty},
    )
    return item, bin_id


async def open_count(client, bin_id):
    r = await client.post("/api/v1/stock-counts", json={"location_id": bin_id})
    assert r.status_code == 201, r.text
    return r.json()


async def test_count_variance_is_adjusted_with_who_and_why(client):
    item, bin_id = await stocked_bin(client, 10)
    count = await open_count(client, bin_id)
    assert count["lines"][0]["system_qty"] == 10

    r = await client.put(f"/api/v1/stock-counts/{count['id']}/lines", json={"lines": [{"item_id": item, "counted_qty": 7}]})
    assert r.json()["lines"][0]["variance"] == -3
    assert (await client.post(f"/api/v1/stock-counts/{count['id']}/submission")).json()["status"] == "submitted"
    assert await stock_at(client, item, bin_id) == 10  # nothing changes before approval

    approved = await client.post(
        f"/api/v1/stock-counts/{count['id']}/approval",
        json={"reason": "Spoilage found on recount"},
        headers=as_user("u-supervisor", ["stock:adjust", "stock:view"]),
    )
    assert approved.status_code == 200 and approved.json()["approved_by"] == "u-supervisor"
    assert await stock_at(client, item, bin_id) == 7

    adjustments = (await client.get("/api/v1/stock-movements", params={"movement_type": "adjustment_out"})).json()["items"]
    assert len(adjustments) == 1
    assert adjustments[0]["quantity"] == 3 and adjustments[0]["actor_id"] == "u-supervisor"
    assert adjustments[0]["reason"] == "Spoilage found on recount" and adjustments[0]["reference_id"] == count["id"]


async def test_item_found_that_system_did_not_know_is_adjusted_in(client):
    _, bin_id = await stocked_bin(client, 2)
    extra = await make_item(client, "EXTRA")
    count = await open_count(client, bin_id)
    base = count["lines"][0]
    await client.put(
        f"/api/v1/stock-counts/{count['id']}/lines",
        json={"lines": [{"item_id": base["item_id"], "counted_qty": 2}, {"item_id": extra, "counted_qty": 5}]},
    )
    await client.post(f"/api/v1/stock-counts/{count['id']}/submission")
    await client.post(f"/api/v1/stock-counts/{count['id']}/approval", json={"reason": "Unlisted stock found"})
    assert await stock_at(client, extra, bin_id) == 5


async def test_cannot_submit_with_uncounted_items(client):
    _, bin_id = await stocked_bin(client, 2)
    count = await open_count(client, bin_id)
    r = await client.post(f"/api/v1/stock-counts/{count['id']}/submission")
    assert r.status_code == 422 and r.json()["details"]["uncounted_item_ids"]


async def test_approval_needs_adjust_permission_and_a_submitted_count(client):
    item, bin_id = await stocked_bin(client, 4)
    count = await open_count(client, bin_id)
    url = f"/api/v1/stock-counts/{count['id']}/approval"
    clerk = as_user("u-clerk", ["stock:transfer", "stock:view"])
    assert (await client.post(url, json={"reason": "because"}, headers=clerk)).status_code == 403
    assert (await client.post(url, json={"reason": "because"})).status_code == 409  # still open
    await client.put(f"/api/v1/stock-counts/{count['id']}/lines", json={"lines": [{"item_id": item, "counted_qty": 4}]})
    await client.post(f"/api/v1/stock-counts/{count['id']}/submission")
    assert (await client.post(url, json={"reason": "all good"})).status_code == 200
    assert (await client.post(url, json={"reason": "again"})).status_code == 409  # cannot apply twice
    assert await stock_at(client, item, bin_id) == 4


async def test_one_unfinished_count_per_location(client):
    _, bin_id = await stocked_bin(client, 1)
    first = await open_count(client, bin_id)
    r = await client.post("/api/v1/stock-counts", json={"location_id": bin_id})
    assert r.status_code == 409 and r.json()["details"]["stock_count_id"] == first["id"]
    await client.post(f"/api/v1/stock-counts/{first['id']}/cancellation")
    assert (await client.post("/api/v1/stock-counts", json={"location_id": bin_id})).status_code == 201


async def test_approval_reason_is_required(client):
    _, bin_id = await stocked_bin(client, 1)
    count = await open_count(client, bin_id)
    r = await client.post(f"/api/v1/stock-counts/{count['id']}/approval", json={"reason": ""})
    assert r.status_code == 422
