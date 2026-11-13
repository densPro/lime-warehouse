from conftest import as_user, make_item


async def test_health_needs_no_auth(client):
    r = await client.get("/health", headers={"X-Test-User": ""})
    assert r.status_code == 200


async def test_missing_token_is_401_with_error_shape(client):
    r = await client.get("/api/v1/items", headers={"X-Test-User": ""})
    assert r.status_code == 401
    body = r.json()
    assert body["code"] == "unauthorized" and body["request_id"]
    assert r.headers["WWW-Authenticate"] == "Bearer"


async def test_missing_permission_is_403(client):
    r = await client.post("/api/v1/items", json={"sku": "X", "name": "X"}, headers=as_user("u", ["stock:view"]))
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"


async def test_request_id_is_echoed_and_in_errors(client):
    r = await client.get("/api/v1/items/nope", headers={**as_user(), "X-Request-ID": "trace-123"})
    assert r.status_code == 404
    assert r.headers["X-Request-ID"] == "trace-123"
    assert r.json()["request_id"] == "trace-123" and r.json()["code"] == "not_found"


async def test_validation_error_shape(client):
    r = await client.post("/api/v1/items", json={"sku": ""})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation_error"
    assert {e["field"] for e in body["errors"]} >= {"body.sku", "body.name"}


async def test_pagination_envelope(client):
    for i in range(3):
        await make_item(client, sku=f"SKU-{i}")
    r = await client.get("/api/v1/items", params={"limit": 2, "offset": 1})
    body = r.json()
    assert (body["total"], body["limit"], body["offset"], len(body["items"])) == (3, 2, 1, 2)
    assert (await client.get("/api/v1/items", params={"limit": 0})).status_code == 422


async def test_duplicate_sku_is_conflict(client):
    await make_item(client, "DUP")
    r = await client.post("/api/v1/items", json={"sku": "dup", "name": "again"})
    assert r.status_code == 409 and r.json()["code"] == "conflict"


async def test_create_returns_location_header(client):
    r = await client.post("/api/v1/items", json={"sku": "L1", "name": "Lime"})
    assert r.headers["Location"] == f"/api/v1/items/{r.json()['id']}"
