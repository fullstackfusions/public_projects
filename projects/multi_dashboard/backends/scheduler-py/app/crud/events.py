"""Async CRUD operations for the Event resource."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Event
from ..schemas import EventCreate, EventUpdate


async def list_events(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Event], int]:
    """Return a page of events and the total count (for pagination)."""
    count_stmt = select(func.count()).select_from(Event)
    total: int = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Event)
        .options(selectinload(Event.reminders))
        .order_by(Event.start_time)
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(stmt)).scalars().unique().all()
    return list(rows), total


async def get_event(db: AsyncSession, event_id: int) -> Event | None:
    stmt = (
        select(Event)
        .where(Event.id == event_id)
        .options(selectinload(Event.reminders))
    )
    return (await db.execute(stmt)).scalars().first()


async def create_event(db: AsyncSession, event_data: EventCreate) -> Event:
    event = Event(**event_data.model_dump())
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def update_event(
    db: AsyncSession, event: Event, update_data: EventUpdate
) -> Event:
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def delete_event(db: AsyncSession, event: Event) -> None:
    await db.delete(event)
    await db.commit()


__all__ = ["create_event", "delete_event", "get_event", "list_events", "update_event"]
