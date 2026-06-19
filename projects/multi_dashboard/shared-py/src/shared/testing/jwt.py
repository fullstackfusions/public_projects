"""JWT helpers for tests — mint a valid bearer token without spinning up
auth-py."""
from __future__ import annotations

import pytest

from ..auth import encode_jwt


@pytest.fixture
def auth_headers_factory():
    """Returns a factory that mints a Bearer header for a given user::

        def test_protected(auth_headers_factory):
            headers = auth_headers_factory(
                secret="testkey1234567890",
                sub="user-1",
                email="demo@example.com",
                role="user",
            )
            ...
    """

    def _factory(
        secret: str,
        sub: str = "test-user",
        *,
        email: str | None = None,
        role: str = "user",
        algorithm: str = "HS256",
        expires_in_seconds: int = 3600,
    ) -> dict[str, str]:
        token = encode_jwt(
            {"sub": sub, "email": email, "role": role},
            secret=secret,
            algorithm=algorithm,
            expires_in_seconds=expires_in_seconds,
        )
        return {"Authorization": f"Bearer {token}"}

    return _factory


__all__ = ["auth_headers_factory"]
