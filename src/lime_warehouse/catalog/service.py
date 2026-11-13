from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lime_warehouse.catalog.models import RECEIVING, Item, Location
from lime_warehouse.shared.errors import Conflict, Invalid, NotFound
from lime_warehouse.shared.pagination import PageParams, paginate


class CatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- items -----------------------------------------------------------
    async def create_item(self, sku: str, name: str, unit: str) -> Item:
        sku = sku.strip().upper()
        if (await self.session.execute(select(Item).where(Item.sku == sku))).scalar_one_or_none():
            raise Conflict(f"An item with SKU {sku} already exists")
        item = Item(sku=sku, name=name.strip(), unit=unit)
        self.session.add(item)
        await self.session.commit()
        return item

    async def require_item(self, item_id: str, *, active: bool = False) -> Item:
        item = await self.session.get(Item, item_id)
        if item is None:
            raise NotFound(f"Item {item_id} not found")
        if active and not item.is_active:
            raise Invalid(f"Item {item.sku} is inactive")
        return item

    async def list_items(self, params: PageParams, q: str | None, active: bool | None):
        stmt = select(Item).order_by(Item.sku)
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(Item.sku.ilike(like) | Item.name.ilike(like))
        if active is not None:
            stmt = stmt.where(Item.is_active == active)
        return await paginate(self.session, stmt, params)

    async def update_item(self, item_id: str, **changes) -> Item:
        item = await self.require_item(item_id)
        for key, value in changes.items():
            if value is not None:
                setattr(item, key, value)
        await self.session.commit()
        return item

    # --- locations -------------------------------------------------------
    async def create_location(self, code: str, zone: str, kind: str) -> Location:
        code = code.strip().upper()
        if (await self.session.execute(select(Location).where(Location.code == code))).scalar_one_or_none():
            raise Conflict(f"A location with code {code} already exists")
        location = Location(code=code, zone=zone, kind=kind)
        self.session.add(location)
        await self.session.commit()
        return location

    async def require_location(self, location_id: str, *, active: bool = False) -> Location:
        location = await self.session.get(Location, location_id)
        if location is None:
            raise NotFound(f"Location {location_id} not found")
        if active and not location.is_active:
            raise Invalid(f"Location {location.code} is inactive")
        return location

    async def list_locations(self, params: PageParams, zone: str | None, active: bool | None):
        stmt = select(Location).order_by(Location.code)
        if zone:
            stmt = stmt.where(Location.zone == zone)
        if active is not None:
            stmt = stmt.where(Location.is_active == active)
        return await paginate(self.session, stmt, params)

    async def update_location(self, location_id: str, **changes) -> Location:
        location = await self.require_location(location_id)
        for key, value in changes.items():
            if value is not None:
                setattr(location, key, value)
        await self.session.commit()
        return location

    async def receiving_location(self) -> Location:
        stmt = select(Location).where(Location.kind == RECEIVING, Location.is_active.is_(True))
        location = (await self.session.execute(stmt.order_by(Location.code))).scalars().first()
        if location is None:
            raise Invalid("No active receiving location is configured")
        return location
