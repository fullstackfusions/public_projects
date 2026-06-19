"""Async data-access functions for NotificationLog."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.log import NotificationLog


async def create_log_entry(
    db: AsyncSession,
    *,
    user_id: str,
    template_id: str,
    dedup_key: str,
    channel: str,
    status: str,
    external_id: str | None = None,
    error: str | None = None,
) -> NotificationLog:
    entry = NotificationLog(
        user_id=user_id,
        template_id=template_id,
        dedup_key=dedup_key,
        channel=channel,
        status=status,
        external_id=external_id,
        error=error,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


async def update_log_status(
    db: AsyncSession,
    entry: NotificationLog,
    *,
    status: str,
    external_id: str | None = None,
    error: str | None = None,
) -> None:
    entry.status = status
    if external_id is not None:
        entry.external_id = external_id
    if error is not None:
        entry.error = error
    await db.flush()


__all__ = ["create_log_entry", "update_log_status"]
