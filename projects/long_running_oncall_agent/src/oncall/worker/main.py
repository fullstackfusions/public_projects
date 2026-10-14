"""Worker: pulls runs off the stream and executes them durably.

Kill a worker mid-run (`make chaos`) and another one reclaims the stream entry and
resumes the LangGraph thread from its last Postgres checkpoint: completed model and
tool calls are not repeated.
"""

from __future__ import annotations

import logging
import signal
import time
from typing import Any

import httpx
from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres import PostgresSaver

from oncall import db, grading, queue, telemetry
from oncall.agent.build import build_agent
from oncall.agent.profiles import ProfileFlags
from oncall.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("worker")
_shutdown = False


def _on_sigterm(*_: Any) -> None:
    global _shutdown
    _shutdown = True  # finish the current run, then exit (crash-stop is `docker kill`)


def _report_from(messages: list) -> dict[str, Any] | None:
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            for call in m.tool_calls:
                if call["name"] == "submit_incident_report":
                    return call["args"]
    return None


def _wait_for_model() -> None:
    s = settings()
    while True:
        try:
            tags = httpx.get(f"{s.ollama_base_url}/api/tags", timeout=5).json()
            names = {m["name"] for m in tags.get("models", [])}
            if s.agent_model in names:
                return
            log.info("waiting for model %s (have %s)", s.agent_model, sorted(names))
        except httpx.HTTPError as e:
            log.info("waiting for ollama: %s", e)
        time.sleep(5)


def execute(run_id: str, checkpointer: PostgresSaver, reclaimed: bool) -> None:
    s = settings()
    run = db.claim_run(run_id, s.worker_name)
    if run is None:
        log.info("run %s already terminal; skipping", run_id)
        return
    flags = ProfileFlags(**run["config"]["flags"])
    ctx = telemetry.RunContext(run_id=run_id, scenario=run["scenario"])
    config = {"configurable": {"thread_id": run_id}, "recursion_limit": 250}

    with telemetry.bind(ctx):
        # Record what this worker actually runs with; the API's view of model/ctx can differ.
        db.set_runtime(run_id, {"agent_model": s.agent_model, "num_ctx": s.agent_num_ctx,
                                "worker": s.worker_name, "max_model_calls": s.max_model_calls})
        agent = build_agent(flags, run["alert"], checkpointer)
        snapshot = agent.get_state(config)
        if snapshot.values:
            # Resume: continue step numbering from the ledger, feed no new input.
            with db.pool().connection() as conn:
                ctx.step = conn.execute(
                    "SELECT count(*) AS n FROM ledger WHERE run_id=%s AND component='agent_model'",
                    (run_id,)).fetchone()["n"]
            ctx.emit("resumed", worker=s.worker_name, attempt=run["attempts"],
                     from_step=ctx.step, reclaimed=reclaimed, pending=list(snapshot.next))
            agent_input = None
        else:
            ctx.emit("started", worker=s.worker_name, profile=run["profile"],
                     scenario=run["scenario"], flags=flags.model_dump())
            agent_input = {"messages": [{"role": "user", "content": run["alert"]}]}

        t0 = time.perf_counter()
        try:
            if agent_input is not None or snapshot.next:
                agent.invoke(agent_input, config)
        except Exception as e:
            log.exception("run %s failed", run_id)
            ctx.emit("failed", error=repr(e)[:1000])
            db.finish_run(run_id, "failed", error=repr(e)[:4000])
            return

        final = agent.get_state(config).values
        messages = final.get("messages", [])
        report = _report_from(messages)
        guard_state = final.get("guard") or {}
        if report:
            status = "succeeded"
        elif guard_state.get("stopped"):
            status = "stopped_by_guard"
        elif ctx.step >= s.max_model_calls:
            status = "budget_exhausted"
        else:
            status = "failed"
        grade = grading.grade(run["scenario"], report)
        grade["access"] = grading.access_stats(queue.client(), run_id)
        grade["wall_s_this_attempt"] = round(time.perf_counter() - t0, 1)
        last_text = next((m.text for m in reversed(messages) if isinstance(m, AIMessage)), "")
        db.finish_run(
            run_id, status, report=report, grade=grade, guard_verdict=guard_state or None,
            extraction=(final.get("scaledown_extraction") or {}).get("fields"),
            error=None if status in ("succeeded", "stopped_by_guard")
            else f"ended without report: {last_text[:500]}",
        )
        ctx.emit("finished", status=status, correct=grade["correct"], steps=ctx.step,
                 reason=grade["reason"])
        log.info("run %s -> %s (correct=%s, steps=%d)", run_id, status, grade["correct"],
                 ctx.step)


def main() -> None:
    signal.signal(signal.SIGTERM, _on_sigterm)
    s = settings()
    db.bootstrap()
    r = queue.client()
    queue.ensure_group(r)
    _wait_for_model()
    with PostgresSaver.from_conn_string(s.database_url) as checkpointer:
        checkpointer.setup()
        log.info("worker %s ready (model=%s, ctx=%d, scaledown=%s)", s.worker_name,
                 s.agent_model, s.agent_num_ctx, s.scaledown_enabled)
        while not _shutdown:
            delivery = queue.next_delivery(r, s.worker_name)
            if delivery is None:
                continue
            log.info("picked run %s (msg %s, reclaimed=%s)", delivery.run_id, delivery.msg_id,
                     delivery.reclaimed)
            with queue.Heartbeat(delivery.msg_id, s.worker_name):
                try:
                    execute(delivery.run_id, checkpointer, delivery.reclaimed)
                except Exception:
                    log.exception("unhandled error executing %s", delivery.run_id)
                    db.finish_run(delivery.run_id, "failed", error="worker error; see logs")
            queue.ack(r, delivery.msg_id)


if __name__ == "__main__":
    main()
