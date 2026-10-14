"""Postgres access: one sync pool per process (worker, bench) plus schema bootstrap."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from oncall.config import settings

TERMINAL_STATUSES = ("succeeded", "failed", "stopped_by_guard", "budget_exhausted")


@lru_cache
def pool() -> ConnectionPool:
    """Process-wide pool. `autocommit` so every helper is its own transaction."""
    p = ConnectionPool(
        settings().database_url,
        min_size=1,
        max_size=8,
        kwargs={"autocommit": True, "row_factory": dict_row},
        open=False,
    )
    p.open(wait=True)
    return p


def bootstrap() -> None:
    """Create app tables (idempotent). Checkpoint tables are set up by the worker."""
    ddl = files("oncall").joinpath("schema.sql").read_text()
    with pool().connection() as conn:
        conn.execute(ddl)


def create_run(
    run_id: UUID, scenario: str, profile: str, config: dict[str, Any], alert: str
) -> None:
    with pool().connection() as conn:
        conn.execute(
            "INSERT INTO runs (id, scenario, profile, config, alert) VALUES (%s,%s,%s,%s,%s)",
            (run_id, scenario, profile, Jsonb(config), alert),
        )


def get_run(run_id: UUID | str) -> dict[str, Any] | None:
    with pool().connection() as conn:
        return conn.execute("SELECT * FROM runs WHERE id = %s", (run_id,)).fetchone()


def claim_run(run_id: UUID | str, worker: str) -> dict[str, Any] | None:
    """Mark a run as running on `worker`; returns None if it is already terminal."""
    with pool().connection() as conn:
        return conn.execute(
            """
            UPDATE runs
               SET status = 'running', worker = %s, attempts = attempts + 1,
                   started_at = COALESCE(started_at, now())
             WHERE id = %s AND status <> ALL(%s)
         RETURNING *
            """,
            (worker, run_id, list(TERMINAL_STATUSES)),
        ).fetchone()


def finish_run(run_id: UUID | str, status: str, **fields: Any) -> None:
    """Set a terminal status plus any of: report, grade, guard_verdict, extraction, error."""
    allowed = {"report", "grade", "guard_verdict", "extraction", "error"}
    cols = {k: v for k, v in fields.items() if k in allowed and v is not None}
    sets = ", ".join(f"{k} = %s" for k in cols)
    params = [Jsonb(v) if k != "error" else v for k, v in cols.items()]
    with pool().connection() as conn:
        conn.execute(
            f"UPDATE runs SET status = %s, finished_at = now(){', ' + sets if sets else ''} "
            "WHERE id = %s",
            (status, *params, run_id),
        )


def set_runtime(run_id: UUID | str, runtime: dict[str, Any]) -> None:
    """Merge the executing worker's real settings into the run's frozen config."""
    with pool().connection() as conn:
        conn.execute("UPDATE runs SET config = config || jsonb_build_object('runtime', %s::jsonb) "
                     "WHERE id = %s", (Jsonb(runtime), run_id))


def set_extraction(run_id: UUID | str, extraction: dict[str, Any]) -> None:
    with pool().connection() as conn:
        conn.execute("UPDATE runs SET extraction = %s WHERE id = %s", (Jsonb(extraction), run_id))


def insert_event(run_id: UUID | str, kind: str, payload: dict[str, Any]) -> int:
    with pool().connection() as conn:
        row = conn.execute(
            "INSERT INTO run_events (run_id, kind, payload) VALUES (%s,%s,%s) RETURNING id",
            (run_id, kind, Jsonb(payload)),
        ).fetchone()
        return int(row["id"])


def insert_ledger(run_id: UUID | str, step: int, component: str, **cols: Any) -> None:
    meta = cols.pop("meta", {}) or {}
    with pool().connection() as conn:
        conn.execute(
            """
            INSERT INTO ledger (run_id, step, component, in_chars, out_chars, in_tokens,
                                out_tokens, latency_ms, ok, meta)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                run_id,
                step,
                component,
                cols.get("in_chars"),
                cols.get("out_chars"),
                cols.get("in_tokens"),
                cols.get("out_tokens"),
                cols.get("latency_ms"),
                cols.get("ok", True),
                Jsonb(json.loads(json.dumps(meta, default=str))),
            ),
        )
