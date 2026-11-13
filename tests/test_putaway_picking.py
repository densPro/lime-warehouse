import asyncio

from conftest import make_item, make_location, receive, recv_id, stock_at


async def stocked_bin(client, qty=10):
    item = await make_item(client)
    bin_id = await make_location(client)
    await receive(client, item, qty)
    r = await client.post(
        "/api/v1/putaways",
        json={"item_id": item, "from_location_id": await recv_id(client), "to_location_id": bin_id, "quantity": qty},
    )
    assert r.status_code == 201, r.text
    return item, bin_id


async def test_putaway_moves_stock_out_of_old_location(client):
    item, bin_id = await stocked_bin(client, 10)
    assert await stock_at(client, item, await recv_id(client)) == 0
    assert await stock_at(client, item, bin_id) == 10


async def test_putaway_more_than_available_is_rejected_and_nothing_moves(client):
    item = await make_item(client)
    bin_id = await make_location(client)
    await receive(client, item, 5)
    r = await client.post(
        "/api/v1/putaways",
        json={"item_id": item, "from_location_id": await recv_id(client), "to_location_id": bin_id, "quantity": 6},
    )
    assert r.status_code == 409 and r.json()["code"] == "insufficient_stock"
    assert r.json()["details"]["available"] == 5
    assert await stock_at(client, item, await recv_id(client)) == 5
    assert await stock_at(client, item, bin_id) == 0


async def test_putaway_to_same_or_inactive_location_is_rejected(client):
    item, bin_id = await stocked_bin(client, 3)
    same = await client.post(
        "/api/v1/putaways", json={"item_id": item, "from_location_id": bin_id, "to_location_id": bin_id, "quantity": 1}
    )
    assert same.status_code == 422
    other = await make_location(client, "B-01")
    await client.patch(f"/api/v1/locations/{other}", json={"is_active": False})
    inactive = await client.post(
        "/api/v1/putaways", json={"item_id": item, "from_location_id": bin_id, "to_location_id": other, "quantity": 1}
    )
    assert inactive.status_code == 422


async def test_pick_reduces_bin_and_completes_list(client):
    item, bin_id = await stocked_bin(client, 10)
    r = await client.post(
        "/api/v1/pick-lists",
        json={"reference": "SO-1", "lines": [{"item_id": item, "location_id": bin_id, "quantity": 4}]},
    )
    assert r.status_code == 201
    pick_list = r.json()
    line = pick_list["lines"][0]["id"]
    done = await client.post(f"/api/v1/pick-lists/{pick_list['id']}/lines/{line}/picks")
    assert done.status_code == 200 and done.json()["status"] == "completed"
    assert await stock_at(client, item, bin_id) == 6
    again = await client.post(f"/api/v1/pick-lists/{pick_list['id']}/lines/{line}/picks")
    assert again.status_code == 409


async def test_partial_picks_track_progress(client):
    item, bin_id = await stocked_bin(client, 10)
    pl = (
        await client.post(
            "/api/v1/pick-lists", json={"lines": [{"item_id": item, "location_id": bin_id, "quantity": 6}]}
        )
    ).json()
    url = f"/api/v1/pick-lists/{pl['id']}/lines/{pl['lines'][0]['id']}/picks"
    first = await client.post(url, json={"quantity": 2})
    assert first.json()["status"] == "in_progress" and first.json()["lines"][0]["picked_qty"] == 2
    assert (await client.post(url, json={"quantity": 5})).status_code == 422  # only 4 left


async def test_cannot_plan_or_pick_from_an_empty_bin(client):
    item, bin_id = await stocked_bin(client, 5)
    too_much = await client.post(
        "/api/v1/pick-lists", json={"lines": [{"item_id": item, "location_id": bin_id, "quantity": 6}]}
    )
    assert too_much.status_code == 409 and too_much.json()["code"] == "insufficient_stock"

    # stock is emptied after the list was planned: the pick itself is refused
    pl = (
        await client.post("/api/v1/pick-lists", json={"lines": [{"item_id": item, "location_id": bin_id, "quantity": 5}]})
    ).json()
    other = await make_location(client, "B-02")
    await client.post(
        "/api/v1/putaways", json={"item_id": item, "from_location_id": bin_id, "to_location_id": other, "quantity": 5}
    )
    r = await client.post(f"/api/v1/pick-lists/{pl['id']}/lines/{pl['lines'][0]['id']}/picks")
    assert r.status_code == 409 and r.json()["code"] == "insufficient_stock"
    assert await stock_at(client, item, other) == 5


async def test_two_pickers_cannot_both_take_the_last_units(file_client):
    client = file_client
    item, bin_id = await stocked_bin(client, 3)
    lists = [
        (await client.post("/api/v1/pick-lists", json={"lines": [{"item_id": item, "location_id": bin_id, "quantity": 3}]})).json()
        for _ in range(2)
    ]
    results = await asyncio.gather(
        *[client.post(f"/api/v1/pick-lists/{p['id']}/lines/{p['lines'][0]['id']}/picks") for p in lists]
    )
    assert sorted(r.status_code for r in results) == [200, 409]
    assert await stock_at(client, item, bin_id) == 0


async def test_cancel_only_open_list(client):
    item, bin_id = await stocked_bin(client, 5)
    pl = (
        await client.post("/api/v1/pick-lists", json={"lines": [{"item_id": item, "location_id": bin_id, "quantity": 2}]})
    ).json()
    assert (await client.post(f"/api/v1/pick-lists/{pl['id']}/cancellation")).json()["status"] == "cancelled"
    assert (await client.post(f"/api/v1/pick-lists/{pl['id']}/cancellation")).status_code == 409
