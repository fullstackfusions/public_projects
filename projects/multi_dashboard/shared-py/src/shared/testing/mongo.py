"""Async Mongo fixtures backed by mongomock-motor.

Despite the name, mongomock-motor presents the same async interface as
``pymongo.AsyncMongoClient`` for tests, so service code that depends on the
real client can be redirected at test time.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def mongo_client():
    """In-memory async Mongo client."""
    try:
        from mongomock_motor import AsyncMongoMockClient
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Install `mongomock-motor` in the test extras: "
            "pip install -e '.[testing]'"
        ) from exc
    return AsyncMongoMockClient()


__all__ = ["mongo_client"]
