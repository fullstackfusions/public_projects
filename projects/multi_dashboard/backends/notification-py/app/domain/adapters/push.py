"""Push adapter — delivers via ntfy (self-hosted push notification server).

Install the ntfy app on iOS/Android, subscribe to your topic, then receive
push notifications when this adapter posts to it.

ntfy docs: https://docs.ntfy.sh/publish/
"""
from __future__ import annotations

import uuid

import httpx
from shared.logging import get_logger

from .base import NotificationError

logger = get_logger(__name__)

# ntfy priority mapping (1=min … 5=max)
PRIORITY_DEFAULT = 3


class PushAdapter:
    channel = "push"

    def __init__(self, base_url: str) -> None:
        # base_url e.g. "http://ntfy" (container) or "http://localhost:8088" (local)
        self._base_url = base_url.rstrip("/")

    async def send(
        self,
        *,
        to: str,  # ntfy topic name
        subject: str,  # used as the push notification title
        body: str,
        priority: int = PRIORITY_DEFAULT,
        **kwargs: object,
    ) -> str:
        """POST to ntfy/{topic} with Title and Priority headers."""
        url = f"{self._base_url}/{to}"
        message_id = str(uuid.uuid4())
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    url,
                    content=body.encode("utf-8"),
                    headers={
                        "Title": subject,
                        "Priority": str(priority),
                        "X-Message-ID": message_id,
                    },
                )
                resp.raise_for_status()
            logger.info(
                "Push notification sent",
                extra={"topic": to, "title": subject, "message_id": message_id},
            )
            return message_id
        except httpx.HTTPError as exc:
            raise NotificationError(f"ntfy send failed: {exc}") from exc


__all__ = ["PushAdapter"]
