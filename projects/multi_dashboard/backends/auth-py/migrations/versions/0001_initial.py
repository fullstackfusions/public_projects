"""initial users table

Revision ID: 0001
Revises:
Create Date: 2026-05-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("picture_url", sa.Text, nullable=True),
        sa.Column("google_sub", sa.String(64), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("role", sa.String(32), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_sub"),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_google_sub", "users", ["google_sub"])


def downgrade() -> None:
    op.drop_index("idx_users_google_sub")
    op.drop_index("idx_users_email")
    op.drop_table("users")
