# Lime Warehouse: Backend Build Brief

This file is the brief for building the **warehouse backend** of the fruit ERP. It lives in `lime-warehouse/`, and the backend is built inside this same folder. Read it fully before writing any code.

## 1. Purpose

Build the backend for the warehouse module of a large ERP system. Its job is to keep the system's view of stock matching the physical warehouse and to make every change traceable.

The problems it must solve:

- **Receiving:** a delivery arrives and the counted quantity does not match the purchase order, or goods are received before they were recorded.
- **Put-away and bin location:** stock is physically moved, but the system still shows the old location.
- **Picking:** someone picks from a bin the system says is empty, or the same item appears in two places.
- **Stock counts and adjustments:** the physical count disagrees with the system, and it is unclear who changed what and why.

**Core principle:** stock quantities are never edited directly. Every change is a recorded movement with user, timestamp and reason, so the full history can be audited. *(This principle is inferred from the four problems above and still needs the owner's confirmation.)*

## 2. Scope

| Domain | Responsibility |
|---|---|
| Receiving | Record deliveries against purchase orders. Flag quantity mismatches and goods received without a prior record. |
| Put-away | Track stock moves between bins so the current location is always correct. |
| Picking | Prevent picks from empty bins. Keep each item's quantity per location consistent so it never appears in two places at once. |
| Stock counts | Reconcile physical counts against system quantities. Record who made each adjustment, when, and why. |

*(Splitting the work into these four domains is the author's reading of the list above.)*

## 3. Authentication and authorization

Use the existing **mango-auth** service (`../mango-auth`).

- This service does not manage users or credentials.
- It only verifies mango-auth identities and enforces the permissions mango-auth grants.
- Use the `mango_auth_client` package that mango-auth provides for token verification and permission checks, instead of re-implementing them.

## 4. Tech stack

Copy the mango-auth stack. Inspect `../mango-auth` and match it exactly:

- Python >= 3.12, `src/` layout
- FastAPI and Uvicorn
- SQLAlchemy 2 (async), asyncpg for PostgreSQL, aiosqlite for tests
- Alembic for migrations
- pydantic-settings for configuration
- PyJWT and httpx (token verification and calls to mango-auth)
- pytest, pytest-asyncio and ruff (line length 110, rules `E,F,I,B,UP`)
- Docker and docker-compose, a Postman collection, and a `docs/` folder

## 5. Architecture

Use a **domain-driven folder structure**. Each business area is its own domain with its own entities, services and API layer. Suggested layout, which the builder may adjust:

```
lime-warehouse/
├── src/lime_warehouse/
│   ├── main.py
│   ├── shared/              # config, db, logging, errors, auth dependencies
│   ├── receiving/           # domain, services, repositories, api
│   ├── putaway/
│   ├── picking/
│   └── stock_counts/
├── tests/
├── alembic/
└── docs/
```

Domains talk to each other through services, never by reaching into each other's tables or repositories directly.

## 6. Engineering requirements

- **API design:** follow the `/api-design-principles` skill for all endpoints (resource naming, HTTP semantics, pagination, versioning, consistent response shapes).
- **Error handling:** follow the `/error-handling-patterns` skill. Use consistent error types and propagation, and return clear, structured errors to API clients.
- **Logging:** implement a structured logger used across all domains. Log requests, stock movements, auth failures and errors, with a correlation ID per request. Never log secrets or tokens. *(The logging details are the author's suggestion.)*

## 7. Documentation

Create a `README.md` inside `lime-warehouse/` covering:

- project overview and the domain structure
- how to run it (local and Docker)
- the mango-auth integration
- the API, error and logging conventions

## 8. Out of scope

- User management, login and credential storage (owned by mango-auth).
- Anything outside warehouse operations (purchasing, sales, finance).
