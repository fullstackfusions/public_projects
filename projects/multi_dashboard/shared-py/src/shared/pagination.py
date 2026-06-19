"""Reusable pagination params + page envelope.

Backends accept ``PageParams`` via ``Depends`` and return ``Page[Item]``::

    @router.get("", response_model=Page[EventOut])
    async def list_events(page: PageParams = Depends()) -> Page[EventOut]:
        items, total = await crud.list_events(db, page.limit, page.offset)
        return Page.build(items, total, page)
"""
from __future__ import annotations

from typing import Generic, Sequence, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field


T = TypeVar("T")


class PageParams(BaseModel):
    """Query params: ``?limit=20&offset=0&sort=-created_at``."""

    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)
    sort: str | None = Field(
        None,
        description="Sort key. Prefix '-' for descending, e.g. '-created_at'.",
    )

    @classmethod
    def as_query(
        cls,
        limit: int = Query(20, ge=1, le=200),
        offset: int = Query(0, ge=0),
        sort: str | None = Query(None),
    ) -> "PageParams":
        """Use as a FastAPI dep: ``Depends(PageParams.as_query)``."""
        return cls(limit=limit, offset=offset, sort=sort)


class Page(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T]
    total: int
    limit: int
    offset: int

    @classmethod
    def build(cls, items: Sequence[T], total: int, page: PageParams) -> "Page[T]":
        return cls(items=list(items), total=total, limit=page.limit, offset=page.offset)


__all__ = ["Page", "PageParams"]
