"""Standardized error envelope and FastAPI exception handlers.

Every backend mounts these handlers via :func:`register_exception_handlers`
so error responses share the same JSON shape, making frontend handling DRY.

Envelope shape::

    {
        "code": "NOT_FOUND",
        "message": "Corporation not found",
        "detail": {"corp_id": "..."},   # optional
        "trace_id": "abc123"            # request-id correlation
    }
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging import get_logger, get_request_id


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------


class ErrorEnvelope(BaseModel):
    """Unified error payload returned by every backend."""

    code: str = Field(..., description="Stable machine-readable error code.")
    message: str = Field(..., description="Human-readable explanation.")
    detail: dict[str, Any] | None = None
    trace_id: str | None = None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AppException(Exception):
    """Base class for application-level errors.

    Subclasses set ``code`` and ``status_code`` once and reuse them.
    """

    code: str = "INTERNAL_ERROR"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str,
        *,
        detail: dict[str, Any] | None = None,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code

    def as_envelope(self) -> ErrorEnvelope:
        return ErrorEnvelope(
            code=self.code,
            message=self.message,
            detail=self.detail,
            trace_id=get_request_id(),
        )


class NotFoundError(AppException):
    code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppException):
    code = "CONFLICT"
    status_code = status.HTTP_409_CONFLICT


class ValidationError(AppException):
    code = "VALIDATION_ERROR"
    status_code = 422  # Unprocessable Content / Entity (RFC 4918)


class AuthError(AppException):
    code = "UNAUTHORIZED"
    status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(AppException):
    code = "FORBIDDEN"
    status_code = status.HTTP_403_FORBIDDEN


class BadGatewayError(AppException):
    code = "BAD_GATEWAY"
    status_code = status.HTTP_502_BAD_GATEWAY


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _envelope_response(
    envelope: ErrorEnvelope, status_code: int
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(envelope.model_dump()),
    )


async def _app_exception_handler(
    request: Request, exc: AppException
) -> JSONResponse:
    logger.warning(
        "AppException %s: %s",
        exc.code,
        exc.message,
        extra={"path": request.url.path, "code": exc.code, "detail": exc.detail},
    )
    return _envelope_response(exc.as_envelope(), exc.status_code)


async def _http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    envelope = ErrorEnvelope(
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail) if exc.detail else "HTTP error",
        trace_id=get_request_id(),
    )
    return _envelope_response(envelope, exc.status_code)


async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    envelope = ErrorEnvelope(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        detail={"errors": jsonable_encoder(exc.errors())},
        trace_id=get_request_id(),
    )
    return _envelope_response(envelope, status_code=ValidationError.status_code)


async def _unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(
        "Unhandled exception on %s", request.url.path, exc_info=exc
    )
    envelope = ErrorEnvelope(
        code="INTERNAL_ERROR",
        message="Internal server error",
        trace_id=get_request_id(),
    )
    return _envelope_response(
        envelope, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all error handlers to a FastAPI app."""
    # Starlette types handlers as (Request, Exception) -> Response. Each handler
    # below narrows `exc` to the specific exception subclass for clarity, which
    # the type checker flags as contravariance. This is safe in practice because
    # a handler is only ever invoked with the exception type it is registered for.
    app.add_exception_handler(AppException, _app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(
        RequestValidationError, _validation_exception_handler  # type: ignore[arg-type]
    )
    app.add_exception_handler(Exception, _unhandled_exception_handler)


__all__ = [
    "AppException",
    "AuthError",
    "BadGatewayError",
    "ConflictError",
    "ErrorEnvelope",
    "ForbiddenError",
    "NotFoundError",
    "ValidationError",
    "register_exception_handlers",
]
