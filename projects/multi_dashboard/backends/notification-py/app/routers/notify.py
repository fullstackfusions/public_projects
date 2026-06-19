"""Notification dispatch endpoints.

POST /notify          — fire a single adapter directly (raw content, no dedup)
POST /notify/template — render a Jinja2 template and fan-out to all enabled
                        channels for the user (with idempotency via dedup_key)

Both endpoints require a valid JWT.
"""
from __future__ import annotations

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from shared.auth import TokenClaims
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..deps import get_current_user, get_db, get_redis
from ..schemas.notification import (
    ChannelResult,
    NotificationRequest,
    NotificationResponse,
    TemplateNotificationRequest,
)
from ..services import dispatcher

router = APIRouter(prefix="/notify", tags=["notify"])


@router.post("", response_model=NotificationResponse)
async def notify_direct(
    payload: NotificationRequest,
    _user: TokenClaims = Depends(get_current_user),
) -> NotificationResponse:
    """Fire a single adapter directly — no template rendering, no dedup check."""
    settings = get_settings()
    result = await dispatcher.dispatch_direct(
        user_id=payload.user_id,
        channel=payload.channel,
        to=payload.to,
        subject=payload.subject,
        body=payload.body,
        settings=settings,
    )
    return NotificationResponse(results=[result])


@router.post("/template", response_model=NotificationResponse)
async def notify_template(
    payload: TemplateNotificationRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),  # type: ignore[type-arg]
    _user: TokenClaims = Depends(get_current_user),
) -> NotificationResponse:
    """Render a Jinja2 template and fan-out to all enabled channels for the user.

    Idempotent: a second call with the same ``dedup_key`` returns
    ``status="skipped"`` for every channel without re-sending.
    """
    settings = get_settings()
    results: list[ChannelResult] = await dispatcher.dispatch_template(
        user_id=payload.user_id,
        template_id=payload.template_id,
        dedup_key=payload.dedup_key,
        context=dict(payload.context),
        db=db,
        redis=redis,
        settings=settings,
    )
    return NotificationResponse(results=results)


__all__ = ["router"]
