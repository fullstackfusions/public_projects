"""initial schema: user_preferences and notification_log tables

Revision ID: 0001
Revises:
Create Date: 2026-05-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── user_preferences ───────────────────────────────────────────────────────
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("ntfy_topic", sa.String(200), nullable=True),
        sa.Column("enabled_channels", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_preferences_user_id"),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"])

    # ── notification_log ───────────────────────────────────────────────────────
    op.create_table(
        "notification_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("template_id", sa.String(100), nullable=False),
        sa.Column("dedup_key", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "template_id", "dedup_key", "channel",
            name="uq_notif_dedup",
        ),
    )
    op.create_index("ix_notification_log_user_id", "notification_log", ["user_id"])
    op.create_index("ix_notification_log_created_at", "notification_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_notification_log_created_at")
    op.drop_index("ix_notification_log_user_id")
    op.drop_table("notification_log")

    op.drop_index("ix_user_preferences_user_id")
    op.drop_table("user_preferences")
