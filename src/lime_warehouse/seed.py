"""Idempotent seed data.

    python -m lime_warehouse.seed                    # required data: the receiving dock (runs on every start)
    python -m lime_warehouse.seed --demo             # plus the default sample set ("fruits")
    python -m lime_warehouse.seed --demo vegetables  # plus a chosen sample set
    python -m lime_warehouse.seed --list             # show the available sample sets

A sample set is a SeedProfile: bins, items, opening stock and purchase orders. Add a new one by
defining a SeedProfile and registering it in PROFILES. Sets use their own bin codes and PO number, so
loading several side by side is safe.

Run `alembic upgrade head` first. Seeding never overwrites rows that already exist.
"""

import argparse
import asyncio
import logging
import sys

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from lime_warehouse.catalog.models import RECEIVING, Item, Location
from lime_warehouse.inventory.models import OPENING_BALANCE, StockMovement
from lime_warehouse.inventory.service import InventoryService
from lime_warehouse.receiving.models import PurchaseOrder
from lime_warehouse.receiving.service import ReceivingService
from lime_warehouse.seed_profiles import PROFILES
from lime_warehouse.shared.config import get_settings
from lime_warehouse.shared.db import make_engine, make_sessionmaker
from lime_warehouse.shared.logging import configure_logging

SYSTEM_ACTOR = "seed"  # stands in for a user id on seeded movements

RECEIVING_DOCK = ("RECV", "dock", RECEIVING)

DEFAULT_PROFILE = "fruits"


async def _ensure_location(session: AsyncSession, code: str, zone: str, kind: str) -> Location:
    found = (await session.execute(select(Location).where(Location.code == code))).scalar_one_or_none()
    if found:
        return found
    location = Location(code=code, zone=zone, kind=kind)
    session.add(location)
    await session.flush()
    return location


async def _ensure_item(session: AsyncSession, sku: str, name: str, unit: str) -> Item:
    found = (await session.execute(select(Item).where(Item.sku == sku))).scalar_one_or_none()
    if found:
        return found
    item = Item(sku=sku, name=name, unit=unit)
    session.add(item)
    await session.flush()
    return item


async def seed_defaults(session: AsyncSession) -> None:
    await _ensure_location(session, *RECEIVING_DOCK)
    await session.commit()


async def seed_demo(session: AsyncSession, profile: str = DEFAULT_PROFILE) -> None:
    if profile not in PROFILES:
        raise ValueError(f"unknown seed profile {profile!r}; choose one of: {', '.join(PROFILES)}")
    data = PROFILES[profile]

    await seed_defaults(session)
    locations = {}
    for code, zone, kind in data.locations:
        locations[code] = await _ensure_location(session, code, zone, kind)
    items = {sku: await _ensure_item(session, sku, name, unit) for sku, name, unit in data.items}
    await session.commit()

    inventory = InventoryService(session)
    for sku, code, qty in data.stock:
        already = (
            await session.execute(
                select(StockMovement.id).where(
                    StockMovement.movement_type == OPENING_BALANCE,
                    StockMovement.item_id == items[sku].id,
                    StockMovement.to_location_id == locations[code].id,
                )
            )
        ).first()
        if not already:
            await inventory.move(
                item_id=items[sku].id,
                quantity=qty,
                movement_type=OPENING_BALANCE,
                actor_id=SYSTEM_ACTOR,
                reason="Demo opening balance",
                to_location_id=locations[code].id,
            )
    await session.commit()

    receiving = ReceivingService(session)
    for po_number, supplier, lines in data.purchase_orders:
        existing_po = select(PurchaseOrder.id).where(PurchaseOrder.po_number == po_number)
        if not (await session.execute(existing_po)).first():
            await receiving.create_purchase_order(
                po_number, supplier, [(items[sku].id, qty) for sku, qty in lines]
            )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lime_warehouse.seed",
        description="Seed the database. Always creates the receiving dock; optionally a sample data set.",
    )
    parser.add_argument(
        "--demo",
        nargs="?",
        const=DEFAULT_PROFILE,
        metavar="PROFILE",
        help=f"also load a sample set ({', '.join(PROFILES)}); without a name loads '{DEFAULT_PROFILE}'",
    )
    parser.add_argument("--list", action="store_true", help="list the available sample sets and exit")
    return parser


async def _cli(argv: list[str]) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:  # argparse exits with 2 on bad usage and 0 on --help
        return int(e.code or 0)

    if args.list:
        for name, data in PROFILES.items():
            print(f"{name:18} {data.description}")
        return 0
    if args.demo is not None and args.demo not in PROFILES:
        print(
            f"error: unknown sample set {args.demo!r}. Choose one of: {', '.join(PROFILES)}",
            file=sys.stderr,
        )
        return 2

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    engine = make_engine(settings.database_url)
    try:
        async with make_sessionmaker(engine)() as session:
            if args.demo is None:
                await seed_defaults(session)
            else:
                await seed_demo(session, args.demo)
        print("Defaults seeded." if args.demo is None else f"Demo data seeded ({args.demo}).")
    except SQLAlchemyError as e:
        logging.getLogger("lime_warehouse.seed").exception("database error while seeding")
        print(
            f"error: database unavailable or not migrated, run `alembic upgrade head` ({type(e).__name__})",
            file=sys.stderr,
        )
        return 1
    finally:
        await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_cli(sys.argv[1:])))
