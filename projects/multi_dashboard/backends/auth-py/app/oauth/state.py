"""Redis-backed OAuth state store for CSRF protection (PKCE flow)."""
from __future__ import annotations

import json
import secrets
from typing import Any

import redis.asyncio as aioredis


class OAuthStateStore:
    """Store and retrieve ephemeral OAuth state from Redis (10-min TTL)."""

    TTL = 600  # seconds

    def __init__(self, redis_client: aioredis.Redis) -> None:  # type: ignore[type-arg,unused-ignore]
        self._r = redis_client

    def _key(self, state: str) -> str:
        return f"oauth:state:{state}"

    async def save(self, data: dict[str, Any], key: str | None = None) -> str:
        """Persist *data* and return the *state* token (generated if not provided)."""
        state = key if key is not None else secrets.token_urlsafe(32)
        await self._r.setex(self._key(state), self.TTL, json.dumps(data))
        return state

    async def pop(self, state: str) -> dict[str, Any] | None:
        """Retrieve and delete the state entry (one-time use)."""
        raw = await self._r.getdel(self._key(state))
        if raw is None:
            return None
        return json.loads(raw)  # type: ignore[no-any-return]
