"""SQLAlchemy 2.x ORM models for scheduler resources.

Uses the modern ``DeclarativeBase`` (not the old ``declarative_base()`` call)
so mypy / pyright see proper types on mapped attributes.
"""
from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base — imported by Alembic env.py for autogenerate."""


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)

    reminders: Mapped[list[Reminder]] = relationship(
        "Reminder",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",  # default eager-load to avoid N+1 on list endpoints
    )


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    remind_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )

    event: Mapped[Event] = relationship("Event", back_populates="reminders")


__all__ = ["Base", "Event", "Reminder"]
