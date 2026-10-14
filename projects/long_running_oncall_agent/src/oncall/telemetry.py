"""Per-run telemetry: the ledger (measurements) and the event timeline (narrative).

A `RunContext` is bound to a contextvar for the duration of a run, so middleware,
tools and the instrumented ScaleDown client can record without threading a run id
through every signature. LangChain's executors copy contextvars into tool threads.
"""

from __future__ import annotations

import contextvars
import json
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import redis
import tiktoken
from langchain_scaledown import ScaledownAPIError, ScaledownClient

from oncall import db
from oncall.config import settings

log = logging.getLogger(__name__)


@lru_cache
def _enc() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """cl100k token count. An approximation for qwen3, used consistently across profiles."""
    return len(_enc().encode(text, disallowed_special=()))


@lru_cache
def _redis() -> redis.Redis:
    return redis.Redis.from_url(settings().redis_url, decode_responses=True)


def channel(run_id: str) -> str:
    return f"run:{run_id}:events"


@dataclass
class RunContext:
    """Mutable per-run state shared by everything that records measurements."""

    run_id: str
    scenario: str
    step: int = 0  # number of agent model calls so far
    counters: dict[str, int] = field(default_factory=dict)

    def emit(self, kind: str, **payload: Any) -> None:
        """Persist a timeline event and fan it out to live SSE subscribers."""
        payload = json.loads(json.dumps(payload, default=str))
        event_id = db.insert_event(self.run_id, kind, payload)
        try:
            _redis().publish(
                channel(self.run_id),
                json.dumps({"id": event_id, "kind": kind, "payload": payload, "ts": time.time()}),
            )
        except redis.RedisError:  # live view is best effort; the row is already durable
            log.warning("event publish failed", exc_info=True)

    def record(self, component: str, **cols: Any) -> None:
        """Append one ledger row at the current step."""
        self.counters[component] = self.counters.get(component, 0) + 1
        db.insert_ledger(self.run_id, self.step, component, **cols)


_current: contextvars.ContextVar[RunContext | None] = contextvars.ContextVar(
    "oncall_run", default=None
)


def current() -> RunContext | None:
    return _current.get()


@contextmanager
def bind(ctx: RunContext) -> Iterator[RunContext]:
    token = _current.set(ctx)
    try:
        yield ctx
    finally:
        _current.reset(token)


def record(component: str, **cols: Any) -> None:
    """Record against the bound run; a no-op outside a run (e.g. ad-hoc scripts)."""
    ctx = current()
    if ctx is not None:
        ctx.record(component, **cols)


def emit(kind: str, **payload: Any) -> None:
    ctx = current()
    if ctx is not None:
        ctx.emit(kind, **payload)


class InstrumentedScaledownClient(ScaledownClient):
    """`ScaledownClient` that writes one ledger row per API call, success or failure.

    Wrapping the client (rather than each middleware) means the stock
    `langchain-scaledown` middlewares are used unmodified and still get measured.
    """

    def _timed(self, component: str, in_text: str, fn, out_of, meta: dict[str, Any]):
        t0 = time.perf_counter()
        try:
            result = fn()
        except ScaledownAPIError as e:
            record(
                component,
                in_chars=len(in_text),
                in_tokens=count_tokens(in_text),
                latency_ms=(time.perf_counter() - t0) * 1000,
                ok=False,
                meta={**meta, "error": str(e)[:300]},
            )
            raise
        out_text, extra = out_of(result)
        record(
            component,
            in_chars=len(in_text),
            out_chars=len(out_text),
            in_tokens=count_tokens(in_text),
            out_tokens=count_tokens(out_text),
            latency_ms=(time.perf_counter() - t0) * 1000,
            meta={**meta, **extra},
        )
        return result

    def summarize(self, text: str, instructions: str | None = None, max_tokens: int = 2048) -> str:
        return self._timed(
            "sd_summarize",
            text,
            lambda: super(InstrumentedScaledownClient, self).summarize(
                text, instructions=instructions, max_tokens=max_tokens
            ),
            lambda r: (r, {}),
            {"max_tokens": max_tokens},
        )

    def compress(self, context: str, prompt: str, rate: Any = "auto") -> dict[str, Any]:
        def out_of(r: dict[str, Any]) -> tuple[str, dict[str, Any]]:
            return str(r.get("compressed_prompt") or ""), {
                "successful": r.get("successful"),
                "sd_original_tokens": r.get("original_prompt_tokens"),
                "sd_compressed_tokens": r.get("compressed_prompt_tokens"),
                "sd_latency_ms": r.get("latency_ms"),
            }

        return self._timed(
            "sd_compress",
            context,
            lambda: super(InstrumentedScaledownClient, self).compress(context, prompt, rate=rate),
            out_of,
            {"query": prompt[:200], "rate": rate},
        )

    def classify(self, text: str, questions: dict[str, Any]) -> dict[str, Any]:
        def out_of(r: dict[str, Any]) -> tuple[str, dict[str, Any]]:
            return json.dumps(r.get("answers") or {}), {"usage": r.get("usage")}

        return self._timed(
            "sd_classify",
            text,
            lambda: super(InstrumentedScaledownClient, self).classify(text, questions),
            out_of,
            {"questions": list(questions)},
        )

    def extract(self, text: str, entities, **kwargs: Any) -> dict[str, Any]:
        def out_of(r: dict[str, Any]) -> tuple[str, dict[str, Any]]:
            return json.dumps(r.get("entities") or []), {"input_tokens": r.get("input_tokens")}

        return self._timed(
            "sd_extract",
            text,
            lambda: super(InstrumentedScaledownClient, self).extract(text, entities, **kwargs),
            out_of,
            {"fields": list(entities)},
        )


@lru_cache
def scaledown_client() -> InstrumentedScaledownClient:
    s = settings()
    return InstrumentedScaledownClient(
        api_key=s.scaledown_api_key, base_url=s.scaledown_base_url, timeout=60.0
    )
