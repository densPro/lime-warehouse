from sqlalchemy import func, select

from lime_warehouse.catalog.models import Item, Location
from lime_warehouse.inventory.models import StockLevel, StockMovement
from lime_warehouse.receiving.models import PurchaseOrder
from lime_warehouse.seed import seed_defaults, seed_demo


async def counts(session):
    result = []
    for model in (Item, Location, StockLevel, StockMovement, PurchaseOrder):
        result.append((await session.execute(select(func.count()).select_from(model))).scalar_one())
    return tuple(result)


async def test_demo_seed_is_idempotent(app):
    async with app.state.sessionmaker() as session:
        await seed_defaults(session)  # RECV already exists in the test fixture
        await seed_demo(session)
        first = await counts(session)
        await seed_demo(session)
        assert await counts(session) == first
    items, locations, levels, movements, orders = first
    assert items >= 50 and locations >= 51 and levels >= 50 and movements >= 50 and orders >= 50


async def test_every_profile_seeds_and_is_idempotent(app):
    from lime_warehouse.seed import PROFILES

    for name, profile in PROFILES.items():
        async with app.state.sessionmaker() as session:
            await seed_demo(session, name)
            first = await counts(session)
            await seed_demo(session, name)
            assert await counts(session) == first
        skus = {sku for sku, _, _ in profile.items}
        assert len(profile.items) >= 50 and len(profile.locations) >= 50
        assert len(profile.stock) >= 50 and len(profile.purchase_orders) >= 50
        assert len({code for code, _, _ in profile.locations}) == len(profile.locations)
        assert all(len(code) <= 32 and len(zone) <= 32 for code, zone, _ in profile.locations)
        assert len(skus) == len(profile.items)
        assert all({sku for sku, _ in lines} <= skus for _, _, lines in profile.purchase_orders)
        assert {sku for sku, _, _ in profile.stock} <= skus
        assert {code for _, code, _ in profile.stock} <= {code for code, _, _ in profile.locations}


async def test_unknown_profile_is_rejected(app):
    import pytest

    async with app.state.sessionmaker() as session:
        with pytest.raises(ValueError, match="unknown seed profile"):
            await seed_demo(session, "nope")
