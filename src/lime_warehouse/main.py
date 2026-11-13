import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from lime_warehouse.catalog import router as catalog_router
from lime_warehouse.inventory import router as inventory_router
from lime_warehouse.models import Base
from lime_warehouse.picking import router as picking_router
from lime_warehouse.putaway import router as putaway_router
from lime_warehouse.receiving import router as receiving_router
from lime_warehouse.shared.auth import MangoAuthClient
from lime_warehouse.shared.config import Settings, get_settings
from lime_warehouse.shared.db import make_engine, make_sessionmaker
from lime_warehouse.shared.errors import WarehouseError
from lime_warehouse.shared.logging import configure_logging, request_id_var
from lime_warehouse.stock_counts import router as stock_counts_router

logger = logging.getLogger("lime_warehouse")


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _error(request: Request, status: int, code: str, detail, headers: dict | None = None, **extra):
    body = {"detail": detail, "code": code, "request_id": _rid(request), **extra}
    return JSONResponse(body, status_code=status, headers=headers)


def create_app(settings: Settings | None = None, create_tables: bool = False, auth=None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)
    engine = make_engine(settings.database_url)
    sessionmaker = make_sessionmaker(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if create_tables:  # dev/test convenience; production uses Alembic migrations
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="lime-warehouse", version="0.1.0", lifespan=lifespan)
    app.state.sessionmaker = sessionmaker
    app.state.auth = auth or MangoAuthClient(
        settings.mango_auth_url, app=settings.mango_auth_app, permission_ttl=settings.permission_ttl
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = rid
        token = request_id_var.set(rid)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            logger.info(
                "request",
                extra={
                    "event": "request",
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            return response
        finally:
            request_id_var.reset(token)

    @app.exception_handler(WarehouseError)
    async def warehouse_error_handler(request: Request, exc: WarehouseError):
        if exc.status >= 500:
            logger.error("%s: %s", exc.code, exc.message, extra={"event": "error", "code": exc.code})
        elif exc.status == 401:
            logger.warning(
                exc.message,
                extra={"event": "auth_failure", "code": exc.code, "path": request.url.path},
            )
        headers = {"WWW-Authenticate": "Bearer"} if exc.status == 401 else None
        extra = {"details": exc.details} if exc.details else {}
        return _error(request, exc.status, exc.code, exc.message, headers, **extra)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        errors = [{"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]} for e in exc.errors()]
        return _error(request, 422, "validation_error", "Request validation failed", errors=errors)

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError):
        # Unique/foreign-key/check violations that slipped past the service-level checks (races).
        logger.warning("integrity error: %s", exc.orig, extra={"event": "error", "code": "conflict"})
        return _error(request, 409, "conflict", "The request conflicts with existing data")

    @app.exception_handler(SQLAlchemyError)
    async def db_handler(request: Request, exc: SQLAlchemyError):
        # Details stay in the log; clients get a generic message.
        logger.exception("database error", exc_info=exc, extra={"event": "error"})
        if isinstance(exc, OperationalError):
            return _error(request, 503, "service_unavailable", "Service temporarily unavailable")
        return _error(request, 500, "internal_error", "Internal server error")

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.exception("unhandled error", exc_info=exc, extra={"event": "error"})
        return _error(request, 500, "internal_error", "Internal server error")

    @app.get("/health", tags=["meta"])
    async def health():
        return {"status": "ok"}

    for module in (
        catalog_router,
        inventory_router,
        receiving_router,
        putaway_router,
        picking_router,
        stock_counts_router,
    ):
        app.include_router(module.router)
    return app


def app_factory() -> FastAPI:
    return create_app()
