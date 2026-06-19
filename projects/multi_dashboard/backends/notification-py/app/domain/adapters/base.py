"""NotificationAdapter Protocol and shared error type.

All adapters satisfy this Protocol — callers type-hint against it so the
dispatcher is decoupled from concrete implementations.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


class NotificationError(Exception):
    """Raised by any adapter when delivery fails after its own retry logic."""


@runtime_checkable
class NotificationAdapter(Protocol):
    """Minimal interface every channel adapter must implement."""

    channel: str  # "email" | "push" | "whatsapp"

    async def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        **kwargs: object,
    ) -> str:
        """Deliver the notification.

        Returns an opaque external message ID on success.
        Raises :class:`NotificationError` on any unrecoverable failure.
        """
        ...


__all__ = ["NotificationAdapter", "NotificationError"]
