"""initial schema: events and reminders tables

Revision ID: 0001
Revises:
Create Date: 2026-05-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_id", "events", ["id"])
    op.create_index("ix_events_start_time", "events", ["start_time"])

    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("message", sa.String(255), nullable=False),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reminders_id", "reminders", ["id"])
    op.create_index("ix_reminders_remind_at", "reminders", ["remind_at"])
    op.create_index("ix_reminders_event_id", "reminders", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_reminders_event_id")
    op.drop_index("ix_reminders_remind_at")
    op.drop_index("ix_reminders_id")
    op.drop_table("reminders")

    op.drop_index("ix_events_start_time")
    op.drop_index("ix_events_id")
    op.drop_table("events")
