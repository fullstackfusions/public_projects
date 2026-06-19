"""WhatsApp adapter — delivers via WAHA (WhatsApp HTTP API, self-hosted).

WAHA runs a headless WhatsApp Web session.  Scan the QR code once with your
phone, then use this adapter to send messages.

⚠️  WAHA uses the unofficial WhatsApp Web protocol.  For personal / dev use
only.  Do not use in production services without switching to the official
Meta Cloud API (swap this adapter for a MetaCloudAdapter — same Protocol).

WAHA docs: https://waha.devlike.pro/docs/how-to/send-messages/
"""
from __future__ import annotations

import uuid

import httpx
from shared.logging import get_logger

from .base import NotificationError

logger = get_logger(__name__)


class WhatsAppAdapter:
    channel = "whatsapp"

    def __init__(self, base_url: str, session: str = "default", api_key: str | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session
        self._headers = {"X-Api-Key": api_key} if api_key else {}

    async def send(
        self,
        *,
        to: str,  # E.164 phone number, e.g. "+14155552671"
        subject: str,  # ignored by WhatsApp (no subject concept)
        body: str,
        **kwargs: object,
    ) -> str:
        """POST to WAHA /api/sendText."""
        # WAHA expects the chat ID in the form "<number>@c.us"
        # Strip leading "+" so it becomes "14155552671@c.us"
        phone = to.lstrip("+")
        chat_id = f"{phone}@c.us"
        message_id = str(uuid.uuid4())

        try:
            async with httpx.AsyncClient(timeout=10.0, headers=self._headers) as client:
                resp = await client.post(
                    f"{self._base_url}/api/sendText",
                    json={
                        "session": self._session,
                        "chatId": chat_id,
                        "text": body,
                    },
                )
                resp.raise_for_status()
            logger.info(
                "WhatsApp message sent",
                extra={"to": chat_id, "message_id": message_id},
            )
            return message_id
        except httpx.HTTPError as exc:
            raise NotificationError(f"WAHA send failed: {exc}") from exc


__all__ = ["WhatsAppAdapter"]
