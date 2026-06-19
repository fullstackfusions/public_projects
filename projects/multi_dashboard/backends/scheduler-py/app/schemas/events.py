"""Pydantic schemas for the Event resource."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .reminders import ReminderOut  # no circular dep: reminders doesn't import events


class EventBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: str | None = None
    start_time: datetime
    end_time: datetime
    location: str | None = Field(None, max_length=200)


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    location: str | None = Field(None, max_length=200)


class EventOut(EventBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class EventWithReminders(EventOut):
    reminders: list[ReminderOut] = []


__all__ = ["EventBase", "EventCreate", "EventOut", "EventUpdate", "EventWithReminders"]
