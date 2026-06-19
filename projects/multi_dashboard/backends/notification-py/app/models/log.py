"""NotificationLog ORM model.

Records every dispatch attempt. The unique constraint on
(user_id, template_id, dedup_key, channel) enforces idempotency at the DB
level — duplicate inserts raise IntegrityError which the dispatcher treats
as "already sent, skip".
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class NotificationLog(Base):
    __tablename__ = "notification_log"
    __table_args__ = (
        UniqueConstraint("user_id", "template_id", "dedup_key", "channel", name="uq_notif_dedup"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(String(100), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    # "sent" | "failed" | "skipped"
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    external_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )


__all__ = ["NotificationLog"]
