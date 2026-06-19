"""Async CRUD operations for the Reminder resource."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Event, Reminder
from ..schemas import ReminderCreate, ReminderUpdate


async def list_reminders(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Reminder], int]:
    count_stmt = select(func.count()).select_from(Reminder)
    total: int = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Reminder)
        .order_by(Reminder.remind_at)
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), total


async def get_reminder(db: AsyncSession, reminder_id: int) -> Reminder | None:
    return await db.get(Reminder, reminder_id)


async def create_reminder(
    db: AsyncSession, reminder_data: ReminderCreate
) -> Reminder:
    # Verify the parent event exists.
    event_exists = await db.get(Event, reminder_data.event_id)
    if event_exists is None:
        raise ValueError("event_not_found")
    reminder = Reminder(**reminder_data.model_dump())
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder


async def update_reminder(
    db: AsyncSession, reminder: Reminder, update_data: ReminderUpdate
) -> Reminder:
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder


async def delete_reminder(db: AsyncSession, reminder: Reminder) -> None:
    await db.delete(reminder)
    await db.commit()


__all__ = [
    "create_reminder",
    "delete_reminder",
    "get_reminder",
    "list_reminders",
    "update_reminder",
]
