"""Notification dispatcher.

Fan-out logic:
1. Load user preferences from DB.
2. For each enabled channel:
   a. Render the Jinja2 template for that channel.
   b. Attempt INSERT into notification_log — if unique constraint fires
      (IntegrityError) the notification was already sent; skip.
   c. Call the channel adapter with tenacity retry (3 attempts, exp backoff).
   d. On exhaustion push to Redis DLQ and mark the log entry "failed".
3. Return a list of per-channel ChannelResult objects.

One channel failing does NOT abort the others.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import redis.asyncio as aioredis
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from shared.logging import get_logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..config import Settings
from ..crud import log as log_crud
from ..crud import preferences as pref_crud
from ..domain.adapters.base import NotificationAdapter, NotificationError
from ..domain.adapters.email import EmailAdapter
from ..domain.adapters.push import PushAdapter
from ..domain.adapters.whatsapp import WhatsAppAdapter
from ..schemas.notification import ChannelResult

logger = get_logger(__name__)

# Templates are at /app/templates inside the container (mounted volume).
# dispatcher.py lives at /app/app/services/dispatcher.py, so parents[2] = /app.
_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"


def _build_adapters(settings: Settings) -> dict[str, NotificationAdapter]:
    return {
        "email": EmailAdapter(
            host=settings.smtp_host,
            port=settings.smtp_port,
            sender=settings.smtp_from,
            username=settings.smtp_username,
            password=settings.smtp_password,
        ),
        "push": PushAdapter(base_url=settings.ntfy_base_url),
        "whatsapp": WhatsAppAdapter(
            base_url=settings.waha_base_url,
            session=settings.waha_session,
            api_key=settings.waha_api_key,
        ),
    }


def _render_template(template_id: str, channel: str, context: dict[str, object]) -> str:
    """Render templates/<template_id>/<channel>.[html|txt] with Jinja2."""
    ext = "html" if channel == "email" else "txt"
    template_path = _TEMPLATES_DIR / template_id / f"{channel}.{ext}"
    if not template_path.exists():
        # Graceful fallback: render context as plain text
        return str(context)
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR / template_id)),
        autoescape=(ext == "html"),
    )
    try:
        tmpl = env.get_template(f"{channel}.{ext}")
        return tmpl.render(**context)
    except TemplateNotFound:
        return str(context)


def _make_retrying_send(adapter: NotificationAdapter):  # type: ignore[no-untyped-def]
    """Wrap adapter.send with tenacity retry (3 attempts, exponential backoff)."""

    @retry(
        retry=retry_if_exception_type(NotificationError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _send(**kwargs: object) -> str:
        return await adapter.send(**kwargs)  # type: ignore[arg-type]

    return _send


async def dispatch_direct(
    *,
    user_id: str,
    channel: str,
    to: str,
    subject: str,
    body: str,
    settings: Settings,
) -> ChannelResult:
    """Fire a single adapter directly (no template, no dedup, no DB write)."""
    adapters = _build_adapters(settings)
    adapter = adapters.get(channel)
    if adapter is None:
        return ChannelResult(channel=channel, status="failed", error=f"Unknown channel: {channel}")
    try:
        send = _make_retrying_send(adapter)
        ext_id = await send(to=to, subject=subject, body=body)
        return ChannelResult(channel=channel, status="sent", external_id=ext_id)
    except NotificationError as exc:
        return ChannelResult(channel=channel, status="failed", error=str(exc))


async def dispatch_template(
    *,
    user_id: str,
    template_id: str,
    dedup_key: str,
    context: dict[str, object],
    db: AsyncSession,
    redis: aioredis.Redis,  # type: ignore[type-arg]
    settings: Settings,
) -> list[ChannelResult]:
    """Fan-out to all enabled channels for the user, with dedup and DLQ."""
    pref = await pref_crud.get_preference(db, user_id)
    if pref is None or not pref.enabled_channels:
        logger.info(
            "No channels enabled for user — skipping",
            extra={"user_id": user_id, "template_id": template_id},
        )
        return []

    adapters = _build_adapters(settings)
    results: list[ChannelResult] = []

    for channel in pref.enabled_channels:
        adapter = adapters.get(channel)
        if adapter is None:
            results.append(
                ChannelResult(channel=channel, status="failed", error="Unknown channel")
            )
            continue

        # Resolve recipient address for this channel
        to = _resolve_recipient(pref, channel)
        if not to:
            logger.warning(
                "No recipient address for channel — skipping",
                extra={"user_id": user_id, "channel": channel},
            )
            results.append(
                ChannelResult(channel=channel, status="skipped", error="No recipient address")
            )
            continue

        # Render template body for this channel
        body = _render_template(template_id, channel, context)
        subject = f"Notification: {template_id}"

        # Attempt dedup INSERT — IntegrityError means already sent
        try:
            log_entry = await log_crud.create_log_entry(
                db,
                user_id=user_id,
                template_id=template_id,
                dedup_key=dedup_key,
                channel=channel,
                status="pending",
            )
            await db.commit()
        except IntegrityError:
            await db.rollback()
            logger.info(
                "Duplicate notification skipped",
                extra={
                    "user_id": user_id,
                    "template_id": template_id,
                    "dedup_key": dedup_key,
                    "channel": channel,
                },
            )
            results.append(ChannelResult(channel=channel, status="skipped"))
            continue

        # Send with retry
        try:
            send = _make_retrying_send(adapter)
            ext_id = await send(to=to, subject=subject, body=body)
            await log_crud.update_log_status(db, log_entry, status="sent", external_id=ext_id)
            await db.commit()
            results.append(ChannelResult(channel=channel, status="sent", external_id=ext_id))
            logger.info(
                "Notification sent",
                extra={
                    "user_id": user_id,
                    "channel": channel,
                    "template_id": template_id,
                    "dedup_key": dedup_key,
                },
            )
        except NotificationError as exc:
            err = str(exc)
            await log_crud.update_log_status(db, log_entry, status="failed", error=err)
            await db.commit()

            # Push to Redis DLQ for later replay
            dlq_payload = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "template_id": template_id,
                "dedup_key": dedup_key,
                "channel": channel,
                "to": to,
                "subject": subject,
                "body": body,
                "error": err,
            }
            await redis.lpush("notification:dlq", json.dumps(dlq_payload))
            logger.error(
                "Notification failed — pushed to DLQ",
                extra={"user_id": user_id, "channel": channel, "error": err},
            )
            results.append(ChannelResult(channel=channel, status="failed", error=err))

    return results


def _resolve_recipient(pref: object, channel: str) -> str | None:
    """Extract the right address from user preferences for a given channel."""
    if channel == "email":
        return getattr(pref, "email", None)
    if channel == "push":
        return getattr(pref, "ntfy_topic", None)
    if channel == "whatsapp":
        return getattr(pref, "phone", None)
    return None


__all__ = ["dispatch_direct", "dispatch_template"]
