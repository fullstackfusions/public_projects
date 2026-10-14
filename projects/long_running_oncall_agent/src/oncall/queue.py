"""Run queue on Redis Streams: at-least-once delivery with crash recovery.

Lifecycle of a message:
  XADD -> XREADGROUP (one worker owns it, it sits in the group's PEL)
       -> worker heartbeats with XCLAIM ... JUSTID (resets idle time while it runs)
       -> XACK when the run reaches a terminal state.
If the worker dies, heartbeats stop, the entry's idle time grows past
`reclaim_idle_ms`, and another worker's XAUTOCLAIM takes it over. The new owner
resumes the LangGraph thread from its last Postgres checkpoint.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

import redis

from oncall.config import settings

log = logging.getLogger(__name__)


@dataclass
class Delivery:
    msg_id: str
    run_id: str
    reclaimed: bool


def client() -> redis.Redis:
    # redis-py 8 defaults socket_timeout to 5s, which equals our XREADGROUP block time and
    # turns every idle poll into a TimeoutError. Keep it comfortably above block_ms.
    return redis.Redis.from_url(settings().redis_url, decode_responses=True, socket_timeout=30)


def ensure_group(r: redis.Redis) -> None:
    s = settings()
    try:
        r.xgroup_create(s.stream_key, s.consumer_group, id="0", mkstream=True)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def enqueue(r: redis.Redis, run_id: str) -> str:
    return r.xadd(settings().stream_key, {"run_id": run_id})


def next_delivery(r: redis.Redis, consumer: str, block_ms: int = 5000) -> Delivery | None:
    """Prefer abandoned work (crashed workers) over new work, then block for new."""
    s = settings()
    _, claimed, _ = r.xautoclaim(s.stream_key, s.consumer_group, consumer,
                                 min_idle_time=s.reclaim_idle_ms, start_id="0-0", count=1)
    if claimed:
        msg_id, fields = claimed[0]
        if fields:  # entry may have been trimmed; fields is empty then
            return Delivery(msg_id, fields["run_id"], reclaimed=True)
        r.xack(s.stream_key, s.consumer_group, msg_id)
    resp = r.xreadgroup(s.consumer_group, consumer, {s.stream_key: ">"}, count=1, block=block_ms)
    if not resp:
        return None
    msg_id, fields = resp[0][1][0]
    return Delivery(msg_id, fields["run_id"], reclaimed=False)


def ack(r: redis.Redis, msg_id: str) -> None:
    s = settings()
    r.xack(s.stream_key, s.consumer_group, msg_id)


class Heartbeat:
    """Keeps a pending entry's idle time near zero while its run executes."""

    def __init__(self, msg_id: str, consumer: str) -> None:
        self.msg_id, self.consumer = msg_id, consumer
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="heartbeat")

    def _loop(self) -> None:
        s = settings()
        r = client()
        while not self._stop.wait(s.heartbeat_s):
            try:
                r.xclaim(s.stream_key, s.consumer_group, self.consumer, min_idle_time=0,
                         message_ids=[self.msg_id], justid=True)
            except redis.RedisError:
                log.warning("heartbeat failed for %s", self.msg_id, exc_info=True)

    def __enter__(self) -> Heartbeat:
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
