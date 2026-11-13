from dataclasses import dataclass

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class PageParams:
    limit: int
    offset: int


def page_params(
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Rows to skip"),
) -> PageParams:
    return PageParams(limit, offset)


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


async def paginate(session: AsyncSession, stmt: Select, params: PageParams) -> tuple[list, int]:
    """Run `stmt` for one page and return (rows, total matching rows). `stmt` must have a stable ORDER BY."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    rows = (await session.execute(stmt.limit(params.limit).offset(params.offset))).scalars().all()
    return list(rows), total


def page_of(schema: type, rows: list, total: int, params: PageParams) -> dict:
    return {
        "items": [schema.model_validate(r) for r in rows],
        "total": total,
        "limit": params.limit,
        "offset": params.offset,
    }
