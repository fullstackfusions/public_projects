"""Events router — CRUD for calendar events.

All routes are protected: a valid JWT is required (CWE-306).
List endpoints use shared pagination (PageParams / Page[T]).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from shared.auth import TokenClaims
from shared.errors import NotFoundError
from shared.pagination import Page, PageParams
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud import events as crud
from ..deps import get_current_user, get_db
from ..schemas import EventCreate, EventOut, EventUpdate, EventWithReminders

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=Page[EventWithReminders])
async def list_events(
    page: PageParams = Depends(PageParams.as_query),
    db: AsyncSession = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> Page[EventWithReminders]:
    items, total = await crud.list_events(db, limit=page.limit, offset=page.offset)
    return Page.build(items, total, page)  # type: ignore[arg-type]


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    body: EventCreate,
    db: AsyncSession = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> EventOut:
    return await crud.create_event(db, body)  # type: ignore[return-value]


@router.get("/{event_id}", response_model=EventWithReminders)
async def read_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> EventWithReminders:
    event = await crud.get_event(db, event_id)
    if event is None:
        raise NotFoundError("Event not found", detail={"event_id": event_id})
    return event  # type: ignore[return-value]


@router.put("/{event_id}", response_model=EventWithReminders)
async def update_event(
    event_id: int,
    body: EventUpdate,
    db: AsyncSession = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> EventWithReminders:
    event = await crud.get_event(db, event_id)
    if event is None:
        raise NotFoundError("Event not found", detail={"event_id": event_id})
    updated = await crud.update_event(db, event, body)
    return updated  # type: ignore[return-value]


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> Response:
    event = await crud.get_event(db, event_id)
    if event is None:
        raise NotFoundError("Event not found", detail={"event_id": event_id})
    await crud.delete_event(db, event)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
