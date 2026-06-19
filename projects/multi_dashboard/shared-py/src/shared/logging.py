"""Structured JSON logging with request-id context propagation.

Use ``configure_logging("my-service")`` once at startup, then
``get_logger(__name__)`` everywhere.

Every log line is enriched with the ``request_id`` from the current contextvar
(set by ``RequestIdMiddleware``) and the service name.
"""
from __future__ import annotations

import contextvars
import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger


# Contextvar set by RequestIdMiddleware; None outside an HTTP request.
_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

_configured = False


def set_request_id(request_id: str | None) -> contextvars.Token[str | None]:
    """Store ``request_id`` for the current async task; returns a reset token."""
    return _request_id_var.set(request_id)


def get_request_id() -> str | None:
    """Return the current request id, or ``None`` outside of a request."""
    return _request_id_var.get()


class _ContextFilter(logging.Filter):
    """Inject ``service`` and ``request_id`` into every log record."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        record.service = self.service_name
        record.request_id = _request_id_var.get()
        return True


class _JsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that includes timestamp, level, service, request_id."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("level", record.levelname)
        log_record.setdefault("logger", record.name)
        if "service" not in log_record:
            log_record["service"] = getattr(record, "service", None)
        if "request_id" not in log_record:
            log_record["request_id"] = getattr(record, "request_id", None)


def configure_logging(service_name: str, level: str = "INFO") -> None:
    """Install JSON handlers on the root logger.

    Safe to call multiple times; subsequent calls are no-ops.
    """
    global _configured
    if _configured:
        return
    _configured = True

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _JsonFormatter(
            "%(asctime)s %(level)s %(logger)s %(message)s",
            rename_fields={"asctime": "timestamp"},
        )
    )
    handler.addFilter(_ContextFilter(service_name))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # Calm down uvicorn's own access logger — middleware emits richer events.
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("uvicorn.error").handlers = [handler]
    logging.getLogger("uvicorn.error").propagate = False


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger; equivalent to ``logging.getLogger`` but ergonomic."""
    return logging.getLogger(name)


__all__ = [
    "configure_logging",
    "get_logger",
    "get_request_id",
    "set_request_id",
]
