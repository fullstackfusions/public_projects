"""Local-only HS256 JWT helpers and FastAPI auth dependency.

Both the issuer (``auth-py``) and the verifiers (every other backend) use this
module. There is **never** an HTTP call from a verifier to the issuer at
request time — the shared secret in env is the single source of trust.

Token claims
------------
- ``sub``  — user id (string)
- ``email`` — user email
- ``role`` — coarse role string ("user", "admin", ...)
- ``type`` — ``"access"`` or ``"refresh"``
- ``exp``, ``iat``, ``jti`` — standard

CWE notes
---------
- HS256 with ≥256-bit shared secret (CWE-326/327)
- ``jti`` is a UUID4 to enable optional revocation lists (CWE-613)
- ``decode_jwt`` validates ``exp`` and ``type`` strictly (CWE-345)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from .errors import AuthError, ForbiddenError


TokenType = Literal["access", "refresh"]


class TokenClaims(BaseModel):
    """Decoded JWT payload."""

    sub: str = Field(..., description="User id")
    email: str | None = None
    name: str | None = None
    role: str = "user"
    type: TokenType = "access"
    jti: str | None = None
    iat: int | None = None
    exp: int | None = None


# ``tokenUrl`` is used by Swagger UI's "Authorize" button. ``auto_error=False``
# lets us produce a consistent envelope when the header is missing.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)


# ---------------------------------------------------------------------------
# Encode / decode
# ---------------------------------------------------------------------------


def encode_jwt(
    payload: dict[str, Any],
    secret: str,
    algorithm: str = "HS256",
    expires_in_seconds: int = 30 * 60,
    *,
    token_type: TokenType = "access",
) -> str:
    """Encode a JWT with standard claims merged in."""
    now = datetime.now(timezone.utc)
    body: dict[str, Any] = {
        **payload,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
        "jti": payload.get("jti") or str(uuid.uuid4()),
    }
    return jwt.encode(body, secret, algorithm=algorithm)


def decode_jwt(
    token: str,
    secret: str,
    algorithm: str = "HS256",
    *,
    expected_type: TokenType | None = "access",
) -> TokenClaims:
    """Decode and validate a JWT. Raises :class:`AuthError` on failure."""
    try:
        raw = jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError as exc:
        raise AuthError(
            "Invalid or expired token",
            detail={"reason": str(exc)},
        ) from exc

    claims = TokenClaims(**raw)
    if expected_type is not None and claims.type != expected_type:
        raise AuthError(
            "Wrong token type",
            detail={"expected": expected_type, "got": claims.type},
        )
    return claims


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_current_user_factory(
    *,
    secret_provider,
    algorithm: str = "HS256",
):
    """Return a ``get_current_user`` dep bound to a settings provider.

    Usage in a backend::

        from shared.auth import get_current_user_factory
        from .config import get_settings

        get_current_user = get_current_user_factory(
            secret_provider=lambda: get_settings().auth_secret_key,
            algorithm="HS256",
        )

        @router.get("/me")
        async def me(user: TokenClaims = Depends(get_current_user)):
            ...

    The factory pattern keeps :mod:`shared.auth` free of any settings import
    so it stays a pure library module.
    """

    async def get_current_user(
        request: Request,
        token: str | None = Depends(_oauth2_scheme),
    ) -> TokenClaims:
        # Allow header OR query string (?access_token=) for SSE/WebSocket use.
        if token is None:
            token = request.query_params.get("access_token")
        if not token:
            raise AuthError("Missing bearer token")
        return decode_jwt(token, secret_provider(), algorithm=algorithm)

    return get_current_user


def require_role(*allowed_roles: str):
    """Build a dep that enforces the current user's role is in ``allowed_roles``.

    Usage::

        admin_only = require_role("admin")

        @router.delete("/foo", dependencies=[Depends(admin_only)])
        async def delete_foo(): ...
    """

    async def _check(user: TokenClaims) -> TokenClaims:
        if user.role not in allowed_roles:
            raise ForbiddenError(
                "Insufficient role",
                detail={"required": list(allowed_roles), "got": user.role},
            )
        return user

    return _check


__all__ = [
    "TokenClaims",
    "TokenType",
    "encode_jwt",
    "decode_jwt",
    "get_current_user_factory",
    "require_role",
]
