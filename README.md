# lime-warehouse

Warehouse backend for the fruit ERP. It keeps the system's view of stock equal to the physical warehouse and makes every change traceable.

**Core rule:** stock quantities are never edited directly. Every change is a row in the append-only `stock_movements` ledger (who, when, why), written in the same transaction as the quantity change.

Users, passwords and permissions live in [mango-auth](../mango-auth). This service only verifies its tokens.

## Run it

Start mango-auth first (it listens on port 8003), then:

```bash
cp .env.example .env
docker compose up --build                                        # migrates, then serves on :8004
docker compose exec api python -m lime_warehouse.seed --demo fruits   # optional sample data: fruits, vegetables or computers
docker compose down -v # stop and remove the containers and networks and also delete the named volumes
```

API docs: http://localhost:8004/docs

Without Docker (SQLite, for development):

```bash
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
export DATABASE_URL=sqlite+aiosqlite:///./lime_warehouse.db MANGO_AUTH_URL=http://localhost:8003 LOG_JSON=false
.venv/bin/alembic upgrade head
.venv/bin/python -m lime_warehouse.seed --demo
.venv/bin/uvicorn lime_warehouse.main:app_factory --factory --port 8004 --reload
.venv/bin/pytest          # tests use an in-memory database and a fake auth, no mango-auth needed
.venv/bin/ruff check .
```

### Migrations

```bash
.venv/bin/alembic upgrade head                              # apply
.venv/bin/alembic revision --autogenerate -m "describe it"  # after changing a model
.venv/bin/alembic downgrade -1                              # undo the last one
```

### Seeds

`python -m lime_warehouse.seed` is idempotent and never overwrites existing rows.

| Command                             | Creates                                                                                                                                          |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `seed` (runs on every Docker start) | the `RECV` receiving dock, which receipts need                                                                                                   |
| `seed --demo [name]`                | a sample set: 50 storage bins, 50+ items, 60+ opening-stock rows and 50 purchase orders. `name` is `fruits` (default), `vegetables`, `computers` or `electrodomesticos` (in Spanish) |
| `seed --list`                       | lists the sample sets                                                                                                                            |

To load a sample set on every Docker start, set `SEED_DEMO=vegetables` (or another name) in `.env`. Each set uses its own bin codes and PO number, so several can be loaded side by side. To add a set, define a `SeedProfile` in `seed_profiles.py` and register it in `PROFILES`.

## Domains

```
src/lime_warehouse/
├── main.py            app factory, middleware, error handlers
├── models.py          imports every model for Alembic
├── seed.py
├── seed_profiles.py   the sample sets (PROFILES)
├── shared/            config, db, errors, logging, pagination, auth, mango_auth_client
├── catalog/           items and locations (reference data)
├── inventory/         stock levels + the movement ledger; the only writer of stock
├── receiving/         purchase orders, goods receipts, mismatch flags
├── putaway/           moves between bins
├── picking/           pick lists, confirming picks
└── stock_counts/      open -> count -> submit -> approve
```

Each domain has `models.py`, `schemas.py`, `service.py` and `router.py`. Domains call each other's **services**, never each other's tables. `receiving`, `putaway`, `picking` and `stock_counts` all change stock through `InventoryService.move()`.

| Problem                                                   | How it is handled                                                                                                                                                                                                       |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Delivery does not match the order, or arrives unrecorded  | `POST /goods-receipts` always books what was counted, into the `RECV` bin, and flags each line `short`, `over` or `unexpected` (`has_discrepancy` on the receipt).                                                      |
| Stock moved but system shows the old bin                  | `POST /putaways` subtracts from the source and adds to the destination in one transaction.                                                                                                                              |
| Pick from an empty bin, or an item "in two places"        | A pick is one conditional `UPDATE ... WHERE quantity >= n`, so two pickers can never both take the last units. A bin never goes below zero (also a DB check constraint). Failing picks return 409 `insufficient_stock`. |
| Count disagrees with the system, unclear who changed what | A count changes nothing until `approval`. Approval writes one `adjustment_in/out` movement per variance with the approver and a required reason. `GET /stock-movements` is the audit trail.                             |

## Authentication and permissions

Requests carry `Authorization: Bearer <mango-auth access token>` issued for the app in `MANGO_AUTH_APP` (default `erp`). Tokens are verified offline against mango-auth's JWKS and permissions are fetched and cached for `PERMISSION_TTL` seconds, by `shared/mango_auth_client.py`.

`shared/mango_auth_client.py` is a copy of `mango-auth/src/mango_auth_client/__init__.py`. mango-auth is not published as a package, and copying keeps this service's Docker build self-contained. Re-copy it when mango-auth's client changes.

This service reuses permissions that already exist in mango-auth's seeded `erp` app (the Warehouse role holds `stock:*`):

| Permission                          | Allows                                                                                    |
| ----------------------------------- | ----------------------------------------------------------------------------------------- |
| `stock:view`                        | all reads: items, locations, stock levels, movements, receipts, pick lists, counts        |
| `stock:transfer`                    | book a receipt, put away, create/pick/cancel pick lists, open/record/submit/cancel counts |
| `stock:adjust`                      | approve a count (changes stock quantities), create/edit locations                         |
| `purchase:view` / `purchase:create` | read / create purchase orders                                                             |
| `product:create` / `product:edit`   | create / edit items                                                                       |

## API conventions

- Versioned under `/api/v1`. Plural nouns for resources. State changes that are not CRUD are sub-resources: `POST /stock-counts/{id}/approval`, `POST /pick-lists/{id}/lines/{line}/picks`.
- `POST` returns `201` and a `Location` header. List endpoints return `{"items": [...], "total": n, "limit": n, "offset": n}` and accept `limit` (1-200, default 50) and `offset`.
- Quantities are whole units (cases, boxes, crates), stored as integers.
- A `GET /health` endpoint needs no token.

## Errors

Every error has the same body, and the same `request_id` appears in the logs and the `X-Request-ID` response header:

```json
{"detail": "Location holds 5 of this item, 6 requested", "code": "insufficient_stock",
 "request_id": "9f2c...", "details": {"item_id": "...", "location_id": "...", "available": 5}}
```

| Status | `code`                                | When                                                       |
| ------ | ------------------------------------- | ---------------------------------------------------------- |
| 401    | `unauthorized`                        | missing, invalid or expired token                          |
| 403    | `forbidden`                           | token valid, permission missing                            |
| 404    | `not_found`                           | unknown id                                                 |
| 409    | `conflict`, `insufficient_stock`      | duplicate, wrong state for the action, or not enough stock |
| 422    | `validation_error`, `invalid_request` | bad body (`errors` lists fields) or a broken business rule |
| 503    | `service_unavailable`                 | database unreachable, safe to retry                        |
| 500    | `internal_error`                      | unexpected; details only in the log, never in the response |

Expected failures are `WarehouseError` subclasses (`shared/errors.py`) raised by services and turned into responses in one place (`main.py`). Mismatches found during receiving are data (flags on the receipt), not errors.

## Logging

One JSON object per line on stderr (`LOG_JSON=false` for readable text). Every line carries `request_id`, taken from the incoming `X-Request-ID` or generated. Events, by the `event` field:

| `event`          | Level                       | Content                                                                   |
| ---------------- | --------------------------- | ------------------------------------------------------------------------- |
| `request`        | INFO                        | method, path, status, `duration_ms`                                       |
| `stock_movement` | INFO                        | movement id and type, item, quantity, from/to, `actor_id`, reference      |
| `goods_receipt`  | INFO, WARNING if mismatched | receipt id, order, `has_discrepancy`                                      |
| `auth_failure`   | WARNING                     | 401s and denied permissions (with `actor_id` and the missing permissions) |
| `error`          | WARNING/ERROR               | integrity, database and unhandled errors with stack traces                |

Tokens, passwords and `Authorization` headers are never logged, and fields named like them are masked if someone passes them to the logger.

## Postman

Import `postman/lime-warehouse.postman_collection.json` and the environment file next to it. Run the whole collection in order (Collection Runner or `newman run`). **0. Login** logs in to mango-auth, stores the token and starts a fresh `runId` so SKUs and PO numbers never collide. The user needs the Warehouse role (or Admin) in the `erp` app.

More detail: [docs/architecture.md](docs/architecture.md).
