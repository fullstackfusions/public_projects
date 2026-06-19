"""Reminders router — CRUD for event reminders.

All routes are protected: a valid JWT is required (CWE-306).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from shared.auth import TokenClaims
from shared.errors import NotFoundError
from shared.pagination import Page, PageParams
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud import reminders as crud
from ..deps import get_current_user, get_db
from ..schemas import ReminderCreate, ReminderOut, ReminderUpdate

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=Page[ReminderOut])
async def list_reminders(
    page: PageParams = Depends(PageParams.as_query),
    db: AsyncSession = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> Page[ReminderOut]:
    items, total = await crud.list_reminders(db, limit=page.limit, offset=page.offset)
    return Page.build(items, total, page)  # type: ignore[arg-type]


@router.post("", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    body: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> ReminderOut:
    try:
        return await crud.create_reminder(db, body)  # type: ignore[return-value]
    except ValueError as exc:
        if str(exc) == "event_not_found":
            raise NotFoundError(
                "Event not found for reminder", detail={"event_id": body.event_id}
            ) from exc
        raise


@router.get("/{reminder_id}", response_model=ReminderOut)
async def read_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> ReminderOut:
    reminder = await crud.get_reminder(db, reminder_id)
    if reminder is None:
        raise NotFoundError("Reminder not found", detail={"reminder_id": reminder_id})
    return reminder  # type: ignore[return-value]


@router.put("/{reminder_id}", response_model=ReminderOut)
async def update_reminder(
    reminder_id: int,
    body: ReminderUpdate,
    db: AsyncSession = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> ReminderOut:
    reminder = await crud.get_reminder(db, reminder_id)
    if reminder is None:
        raise NotFoundError("Reminder not found", detail={"reminder_id": reminder_id})
    updated = await crud.update_reminder(db, reminder, body)
    return updated  # type: ignore[return-value]


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> Response:
    reminder = await crud.get_reminder(db, reminder_id)
    if reminder is None:
        raise NotFoundError("Reminder not found", detail={"reminder_id": reminder_id})
    await crud.delete_reminder(db, reminder)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
