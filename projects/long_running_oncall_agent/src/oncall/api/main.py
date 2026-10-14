"""HTTP API + dashboard. Creates runs, serves their state, streams their timeline."""

from __future__ import annotations

import asyncio
import json
import uuid
from importlib.resources import files
from typing import Any

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from oncall import db, queue, telemetry
from oncall.agent.profiles import PROFILES, resolve
from oncall.config import settings
from oncall.prodsim.scenarios import SCENARIOS

app = FastAPI(title="oncall-agent")


@app.on_event("startup")
def _startup() -> None:
    db.bootstrap()
    queue.ensure_group(queue.client())


class CreateRun(BaseModel):
    scenario: str
    profile: str = "scaledown_fold"
    overrides: dict[str, Any] | None = None


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return files("oncall.api").joinpath("dashboard.html").read_text()


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    s = settings()
    return {
        "scenarios": [{"id": x.id, "title": x.title, "kind": x.kind} for x in SCENARIOS.values()],
        "profiles": {k: v.model_dump() for k, v in PROFILES.items()},
        "scaledown_enabled": s.scaledown_enabled,
        "agent_model": s.agent_model,
        "num_ctx": s.agent_num_ctx,
    }


def create_run(body: CreateRun) -> dict[str, Any]:
    if body.scenario not in SCENARIOS:
        raise HTTPException(404, f"unknown scenario {body.scenario!r}")
    try:
        flags = resolve(body.profile, body.overrides)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    s = settings()
    run_id = uuid.uuid4()
    config = {"flags": flags.model_dump(), "agent_model": s.agent_model,
              "num_ctx": s.agent_num_ctx, "max_model_calls": s.max_model_calls}
    db.create_run(run_id, body.scenario, body.profile, config, SCENARIOS[body.scenario].alert)
    queue.enqueue(queue.client(), str(run_id))
    return db.get_run(run_id)


@app.post("/api/runs", status_code=201)
def post_run(body: CreateRun) -> dict[str, Any]:
    return create_run(body)


LEDGER_AGG = """
SELECT component,
       count(*)                          AS calls,
       sum(in_tokens)                    AS in_tokens,
       sum(out_tokens)                   AS out_tokens,
       sum(in_chars)                     AS in_chars,
       sum(out_chars)                    AS out_chars,
       round(sum(latency_ms)::numeric)   AS latency_ms,
       sum(CASE WHEN ok THEN 0 ELSE 1 END) AS failures
  FROM ledger WHERE run_id = %s GROUP BY component ORDER BY component
"""

RUNS_LIST = """
SELECT r.id, r.scenario, r.profile, r.status, r.attempts, r.created_at, r.started_at,
       r.finished_at, r.grade->>'correct' AS correct,
       EXTRACT(EPOCH FROM (r.finished_at - r.started_at)) AS wall_s,
       (SELECT count(*) FROM ledger l WHERE l.run_id = r.id AND component='agent_model') AS steps,
       (SELECT sum(in_tokens) FROM ledger l WHERE l.run_id = r.id
         AND component='agent_model') AS agent_in_tokens
  FROM runs r ORDER BY r.created_at DESC LIMIT %s
"""


@app.get("/api/runs")
def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    with db.pool().connection() as conn:
        return conn.execute(RUNS_LIST, (limit,)).fetchall()


@app.get("/api/runs/{run_id}")
def get_run(run_id: uuid.UUID) -> dict[str, Any]:
    run = db.get_run(run_id)
    if run is None:
        raise HTTPException(404, "no such run")
    with db.pool().connection() as conn:
        run["ledger"] = conn.execute(LEDGER_AGG, (run_id,)).fetchall()
        run["context_series"] = conn.execute(
            """SELECT step, in_tokens, round(latency_ms::numeric) AS latency_ms,
                      (meta->>'ollama_prompt_eval_count')::int AS prompt_eval
                 FROM ledger WHERE run_id=%s AND component='agent_model' ORDER BY id""",
            (run_id,)).fetchall()
    return run


def _events_after(run_id: str, after: int) -> list[dict[str, Any]]:
    with db.pool().connection() as conn:
        return conn.execute(
            "SELECT id, kind, payload, extract(epoch from ts) AS ts FROM run_events "
            "WHERE run_id=%s AND id > %s ORDER BY id", (run_id, after)).fetchall()


@app.get("/api/runs/{run_id}/stream")
async def stream(run_id: uuid.UUID, request: Request):
    """SSE: subscribe first, then replay from Postgres, then forward live (deduped by id),
    so no event can fall in the gap between replay and subscription."""
    rid = str(run_id)
    last = int(request.headers.get("last-event-id") or 0)
    r = aioredis.Redis.from_url(settings().redis_url, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(telemetry.channel(rid))

    async def gen():
        nonlocal last
        try:
            for e in await run_in_threadpool(_events_after, rid, last):
                last = e["id"]
                yield {"id": str(e["id"]), "event": e["kind"],
                       "data": json.dumps({**e, "ts": float(e["ts"])}, default=str)}
            while not await request.is_disconnected():
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=10)
                if msg is None:
                    yield {"event": "ping", "data": "{}"}
                    continue
                e = json.loads(msg["data"])
                if e["id"] <= last:
                    continue
                last = e["id"]
                yield {"id": str(e["id"]), "event": e["kind"], "data": json.dumps(e)}
                await asyncio.sleep(0)
        finally:
            await pubsub.unsubscribe()
            await r.aclose()

    return EventSourceResponse(gen())
