"""Smoke tests for shared-py — ensures every submodule imports cleanly and
the JWT round-trip works."""
from __future__ import annotations

import os

import pytest

# Required for AppSettings instantiation
os.environ.setdefault("SERVICE_NAME", "shared-smoke")
os.environ.setdefault(
    "AUTH_SECRET_KEY", "test-secret-key-please-change-in-production"
)


def test_imports() -> None:
    """Every public module imports without raising."""
    import shared
    import shared.config
    import shared.logging
    import shared.errors
    import shared.auth
    import shared.cors
    import shared.middleware
    import shared.pagination
    import shared.db.sql
    import shared.db.mongo
    import shared.testing  # noqa: F401

    assert shared.__version__


def test_settings_loads_from_env() -> None:
    from shared.config import AppSettings

    s = AppSettings()  # picks up env defaults set at module top
    assert s.service_name == "shared-smoke"
    assert s.auth_secret_key.startswith("test-secret")
    assert s.auth_algorithm == "HS256"


def test_jwt_roundtrip() -> None:
    from shared.auth import decode_jwt, encode_jwt

    secret = "test-secret-key-please-change-in-production"
    token = encode_jwt(
        {"sub": "user-42", "email": "alice@example.com", "role": "admin"},
        secret=secret,
        expires_in_seconds=60,
    )
    claims = decode_jwt(token, secret)
    assert claims.sub == "user-42"
    assert claims.email == "alice@example.com"
    assert claims.role == "admin"
    assert claims.type == "access"


def test_jwt_wrong_secret_raises() -> None:
    from shared.auth import decode_jwt, encode_jwt
    from shared.errors import AuthError

    token = encode_jwt({"sub": "x"}, "secret-a-1234567890", expires_in_seconds=60)
    with pytest.raises(AuthError):
        decode_jwt(token, "secret-b-0987654321")


def test_jwt_wrong_type_raises() -> None:
    from shared.auth import decode_jwt, encode_jwt
    from shared.errors import AuthError

    secret = "test-secret-key-please-change-in-production"
    token = encode_jwt({"sub": "x"}, secret, token_type="refresh", expires_in_seconds=60)
    with pytest.raises(AuthError):
        decode_jwt(token, secret, expected_type="access")
    # But fine when expected type matches:
    claims = decode_jwt(token, secret, expected_type="refresh")
    assert claims.type == "refresh"


def test_error_envelope_shape() -> None:
    from shared.errors import ErrorEnvelope, NotFoundError

    err = NotFoundError("Thing missing", detail={"id": "abc"})
    env = err.as_envelope()
    assert env.code == "NOT_FOUND"
    assert env.message == "Thing missing"
    assert env.detail == {"id": "abc"}
    assert isinstance(env, ErrorEnvelope)


def test_pagination() -> None:
    from shared.pagination import Page, PageParams

    page = PageParams(limit=10, offset=20)
    result = Page.build([1, 2, 3], total=100, page=page)
    assert result.items == [1, 2, 3]
    assert result.total == 100
    assert result.limit == 10
    assert result.offset == 20


def test_cors_rejects_wildcard_with_credentials() -> None:
    from fastapi import FastAPI

    from shared.cors import add_cors

    with pytest.raises(ValueError):
        add_cors(FastAPI(), ["*"], allow_credentials=True)
