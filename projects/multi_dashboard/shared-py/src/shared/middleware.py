"""HTTP middleware: request id propagation, access log, timing.

All three are wired up by :func:`install_middleware`. Backends call::

    from shared.middleware import install_middleware
    install_middleware(app)
"""
from __future__ import annotations

import time
import uuid
from typing import Awaitable, Callable

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .logging import get_logger, set_request_id


_REQUEST_ID_HEADER = "X-Request-ID"

logger = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Propagate ``X-Request-ID`` and expose it via the logging contextvar.

    Generates a UUID4 when no inbound header is present. Always echoes the id
    back in the response so the frontend can include it in bug reports.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(_REQUEST_ID_HEADER) or uuid.uuid4().hex
        token = set_request_id(request_id)
        try:
            response = await call_next(request)
        finally:
            # Reset the contextvar even on exception.
            from .logging import _request_id_var  # local import avoids cycles

            _request_id_var.reset(token)
        response.headers[_REQUEST_ID_HEADER] = request_id
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """One JSON log line per request: method, path, status, duration_ms."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


def install_middleware(app: FastAPI) -> None:
    """Install the standard middleware stack in the correct order.

    Starlette runs middleware in reverse-added order, so RequestId must be
    added LAST to wrap everything else.
    """
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)


__all__ = ["AccessLogMiddleware", "RequestIdMiddleware", "install_middleware"]
