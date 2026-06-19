"""Pydantic request/response schemas for notification-backend."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# ── Direct dispatch (single channel, raw content) ────────────────────────────

class NotificationRequest(BaseModel):
    """POST /notify — fire a single adapter directly, no template, no dedup."""

    user_id: str = Field(..., description="Target user (JWT sub claim)")
    channel: Literal["email", "push", "whatsapp"] = Field(..., description="Delivery channel")
    to: str = Field(..., description="Recipient address (email / phone / ntfy topic)")
    subject: str = Field(..., description="Subject / title (ignored for whatsapp)")
    body: str = Field(..., description="Message body (plain text or HTML for email)")


class ChannelResult(BaseModel):
    channel: str
    status: Literal["sent", "failed", "skipped"]
    external_id: str | None = None
    error: str | None = None


class NotificationResponse(BaseModel):
    results: list[ChannelResult]


# ── Template dispatch (fan-out via user preferences) ─────────────────────────

class TemplateNotificationRequest(BaseModel):
    """POST /notify/template — render a Jinja2 template and fan out to all
    enabled channels for this user."""

    user_id: str = Field(..., description="Target user (JWT sub claim)")
    template_id: str = Field(..., description="Template folder name under templates/")
    dedup_key: str = Field(..., description="Idempotency key — duplicate calls are no-ops")
    context: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict, description="Variables passed to the Jinja2 template"
    )


# ── User preferences ─────────────────────────────────────────────────────────

class UserPreferenceOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: str
    email: str | None
    phone: str | None
    ntfy_topic: str | None
    enabled_channels: list[str]
    created_at: datetime
    updated_at: datetime


class UserPreferenceUpdate(BaseModel):
    """PUT /preferences/me — all fields optional; only provided fields are updated."""

    email: str | None = None
    phone: str | None = None
    ntfy_topic: str | None = None
    enabled_channels: list[Literal["email", "push", "whatsapp"]] | None = None


__all__ = [
    "NotificationRequest",
    "ChannelResult",
    "NotificationResponse",
    "TemplateNotificationRequest",
    "UserPreferenceOut",
    "UserPreferenceUpdate",
]
