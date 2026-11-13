import httpx
import pytest_asyncio
from fastapi import HTTPException, Request

from lime_warehouse.catalog.models import RECEIVING, Location
from lime_warehouse.main import create_app
from lime_warehouse.shared.auth import Principal
from lime_warehouse.shared.config import Settings

ALL = ["stock:view", "stock:transfer", "stock:adjust", "product:create", "product:edit", "purchase:create", "purchase:view"]


class FakeAuth:
    """Stands in for mango-auth. The header is `X-Test-User: <user id>[:perm,perm]` (default: everything)."""

    async def current_user(self, request: Request) -> Principal:
        raw = request.headers.get("x-test-user")
        if not raw:
            raise HTTPException(401, "Missing bearer token")
        sub, _, perms = raw.partition(":")
        return Principal(sub, "erp", [], perms.split(",") if perms else ALL)


def as_user(user_id: str = "u-clerk", permissions: list[str] | None = None) -> dict:
    return {"X-Test-User": user_id + (":" + ",".join(permissions) if permissions is not None else "")}


@pytest_asyncio.fixture
async def app():
    app = create_app(
        Settings(database_url="sqlite+aiosqlite:///:memory:", log_level="WARNING"),
        create_tables=True,
        auth=FakeAuth(),
    )
    async with app.router.lifespan_context(app):
        async with app.state.sessionmaker() as session:
            session.add(Location(code="RECV", zone="dock", kind=RECEIVING))
            await session.commit()
        yield app


@pytest_asyncio.fixture
async def file_client(tmp_path):
    """Like `client`, but on a file database so every session gets its own connection (real concurrency)."""
    app = create_app(
        Settings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'wh.db'}", log_level="WARNING"),
        create_tables=True,
        auth=FakeAuth(),
    )
    async with app.router.lifespan_context(app):
        async with app.state.sessionmaker() as session:
            session.add(Location(code="RECV", zone="dock", kind=RECEIVING))
            await session.commit()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://wh", headers=as_user()
        ) as c:
            yield c


@pytest_asyncio.fixture
async def client(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://wh", headers=as_user()
    ) as c:
        yield c


async def make_item(client, sku="MANGO-10", name="Mango"):
    r = await client.post("/api/v1/items", json={"sku": sku, "name": name})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def make_location(client, code="A-01"):
    r = await client.post("/api/v1/locations", json={"code": code, "zone": "ambient"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def recv_id(client):
    r = await client.get("/api/v1/locations", params={"zone": "dock"})
    return r.json()["items"][0]["id"]


async def receive(client, item_id, qty, po_id=None):
    body = {"lines": [{"item_id": item_id, "received_qty": qty}]}
    if po_id:
        body["purchase_order_id"] = po_id
    r = await client.post("/api/v1/goods-receipts", json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def stock_at(client, item_id, location_id) -> int:
    r = await client.get("/api/v1/stock-levels", params={"item_id": item_id, "location_id": location_id})
    items = r.json()["items"]
    return items[0]["quantity"] if items else 0
