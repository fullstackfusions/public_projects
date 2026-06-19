from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings


class RedisJobStore:
    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None

    async def client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(get_settings().redis_url, decode_responses=True)
        return self._client

    def _key(self, msg_id: str) -> str:
        return f"agentic_chat:job:{msg_id}"

    async def create_job(self, msg_id: str, conversation_id: str) -> None:
        r = await self.client()
        now = datetime.now().isoformat()
        job: dict[str, Any] = {
            "msg_id": msg_id,
            "conversation_id": conversation_id,
            "status": "processing",
            "steps": [],
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        await r.setex(self._key(msg_id), get_settings().job_ttl_seconds, json.dumps(job))

    async def get_job(self, msg_id: str) -> dict | None:
        r = await self.client()
        data = await r.get(self._key(msg_id))
        return json.loads(data) if data else None

    async def add_step(self, msg_id: str, step: dict) -> None:
        r = await self.client()
        data = await r.get(self._key(msg_id))
        if not data:
            return
        job = json.loads(data)
        job["steps"].append(step)
        job["updated_at"] = datetime.now().isoformat()
        ttl = await r.ttl(self._key(msg_id))
        await r.setex(self._key(msg_id), max(ttl, 60), json.dumps(job))

    async def complete_job(self, msg_id: str, result: str) -> None:
        await self._update(msg_id, status="complete", result=result)

    async def fail_job(self, msg_id: str, error: str) -> None:
        await self._update(msg_id, status="error", error=error)

    async def _update(self, msg_id: str, **fields: Any) -> None:
        r = await self.client()
        data = await r.get(self._key(msg_id))
        if not data:
            return
        job = json.loads(data)
        job.update(fields)
        job["updated_at"] = datetime.now().isoformat()
        ttl = await r.ttl(self._key(msg_id))
        await r.setex(self._key(msg_id), max(ttl, 60), json.dumps(job))


job_store = RedisJobStore()
