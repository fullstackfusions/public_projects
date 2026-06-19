"""PyMongo AsyncMongoClient factory.

Uses ``pymongo.AsyncMongoClient`` (PyMongo 4.9+), the *native* async client —
not Motor. Backends construct one client per process and reuse it across
requests::

    from shared.db.mongo import make_async_mongo_client

    client = make_async_mongo_client(settings.mongo_uri)
    db = client[settings.mongo_db_name]
    corporations = db["corporations"]
"""
from __future__ import annotations

from typing import TYPE_CHECKING

# AsyncMongoClient lives at the top-level of pymongo as of 4.9+. Importing
# eagerly with a guard so misconfigured envs fail fast at startup.
try:
    from pymongo import AsyncMongoClient  # type: ignore[attr-defined]
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pymongo>=4.9 is required for AsyncMongoClient. "
        "Pin `pymongo>=4.9,<5` in your service requirements."
    ) from exc


if TYPE_CHECKING:
    from pymongo.asynchronous.collection import AsyncCollection
    from pymongo.asynchronous.database import AsyncDatabase


def make_async_mongo_client(
    uri: str,
    *,
    server_selection_timeout_ms: int = 5000,
    app_name: str | None = None,
) -> AsyncMongoClient:
    """Construct an :class:`AsyncMongoClient`. Safe to share across requests."""
    return AsyncMongoClient(
        uri,
        serverSelectionTimeoutMS=server_selection_timeout_ms,
        appname=app_name,
    )


def get_collection(
    client: AsyncMongoClient, db_name: str, collection_name: str
) -> "AsyncCollection":
    """Convenience getter — equivalent to ``client[db_name][collection_name]``."""
    return client[db_name][collection_name]


def get_database(client: AsyncMongoClient, db_name: str) -> "AsyncDatabase":
    return client[db_name]


__all__ = [
    "AsyncMongoClient",
    "make_async_mongo_client",
    "get_collection",
    "get_database",
]
