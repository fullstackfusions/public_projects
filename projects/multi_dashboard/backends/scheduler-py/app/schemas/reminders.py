"""Pydantic schemas for the Reminder resource."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReminderBase(BaseModel):
    message: str = Field(..., max_length=255)
    remind_at: datetime
    event_id: int


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    message: str | None = Field(None, max_length=255)
    remind_at: datetime | None = None


class ReminderOut(ReminderBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


__all__ = ["ReminderBase", "ReminderCreate", "ReminderOut", "ReminderUpdate"]
