"""Email adapter — delivers via SMTP using aiosmtplib.

Local dev: points at Mailpit (port 1025, no auth).
Production: swap SMTP_HOST/PORT/USERNAME/PASSWORD env vars — code unchanged.
"""
from __future__ import annotations

import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from shared.logging import get_logger

from .base import NotificationError

logger = get_logger(__name__)


class EmailAdapter:
    channel = "email"

    def __init__(
        self,
        host: str,
        port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._sender = sender
        self._username = username
        self._password = password

    async def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        **kwargs: object,
    ) -> str:
        """Send an email. Body can be plain text or HTML."""
        message_id = str(uuid.uuid4())

        # Build a simple MIME message.  If body contains HTML tags use html part.
        is_html = "<" in body and ">" in body
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._sender
        msg["To"] = to
        msg["Message-ID"] = f"<{message_id}@notification-backend>"

        if is_html:
            msg.attach(MIMEText(body, "html"))
        else:
            msg.attach(MIMEText(body, "plain"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                # Mailpit doesn't use TLS on port 1025
                use_tls=False,
                start_tls=False,
            )
            logger.info(
                "Email sent",
                extra={"to": to, "subject": subject, "message_id": message_id},
            )
            return message_id
        except Exception as exc:
            raise NotificationError(f"SMTP send failed: {exc}") from exc


__all__ = ["EmailAdapter"]
