"""Aggregate a bench batch into results/<stamp>.md / .json. Every number is a query
over the ledger, run rows, or event log; nothing is estimated here.

    docker compose --profile bench run --rm bench python -m oncall.bench.report results/raw/X.json
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from oncall import db

PER_RUN = """
SELECT component, count(*) AS n, coalesce(sum(in_tokens),0) AS in_tok,
       coalesce(max(in_tokens),0) AS max_in_tok, coalesce(sum(latency_ms),0) AS ms,
       coalesce(sum((meta->>'ollama_prompt_eval_count')::int),0) AS prompt_eval,
       coalesce(sum((meta->'usage'->>'cost')::float),0) AS sd_cost,
       sum(CASE WHEN ok THEN 0 ELSE 1 END) AS failures
  FROM ledger WHERE run_id=%s GROUP BY component
"""


def run_metrics(run_id: str) -> dict[str, Any]:
    run = db.get_run(run_id)
    with db.pool().connection() as conn:
        comp = {r["component"]: r for r in conn.execute(PER_RUN, (run_id,)).fetchall()}
        events = conn.execute("SELECT kind, payload FROM run_events WHERE run_id=%s ORDER BY id",
                              (run_id,)).fetchall()
    am = comp.get("agent_model", {})
    sd = [c for k, c in comp.items() if k.startswith("sd_")]
    grade = run["grade"] or {}
    access = grade.get("access", {})

    # First tool-call count at which each detector would flag non-progress (p >= 0.6).
    first_flag: dict[str, int] = {}
    for e in events:
        if e["kind"] != "guard_check":
            continue
        for v in e["payload"]["verdicts"]:
            p = max(v["probs"].get("looping", 0), v["probs"].get("drifting", 0))
            if p >= 0.6 and v["detector"] not in first_flag:
                first_flag[v["detector"]] = e["payload"]["tool_calls"]

    wall = None
    if run["finished_at"] and run["started_at"]:
        wall = (run["finished_at"] - run["started_at"]).total_seconds()
    return {
        "run_id": run_id, "scenario": run["scenario"], "profile": run["profile"],
        "status": run["status"], "correct": bool(grade.get("correct")),
        "attempts": run["attempts"], "wall_s": wall,
        "steps": am.get("n", 0),
        "agent_ctx_tokens_total": am.get("in_tok", 0),
        "agent_ctx_tokens_peak": am.get("max_in_tok", 0),
        "agent_prompt_eval_total": am.get("prompt_eval", 0),
        "agent_model_s": am.get("ms", 0) / 1000,
        "sd_calls": sum(c["n"] for c in sd),
        "sd_s": sum(c["ms"] for c in sd) / 1000,
        "sd_failures": sum(c["failures"] for c in sd),
        "sd_cost_usd_reported": sum(c["sd_cost"] for c in sd),
        "local_summarize_s": comp.get("local_summarize", {}).get("ms", 0) / 1000,
        "summaries": sum(1 for e in events if e["kind"] == "summarized"),
        "nudges": sum(1 for e in events if e["kind"] == "guard_nudge"),
        "guard_stopped": run["status"] == "stopped_by_guard",
        "prodsim_calls": access.get("prodsim_calls"),
        "calls_after_first_failure": access.get("calls_after_first_failure"),
        "max_identical_calls": access.get("max_identical_calls"),
        "first_flag_at_tool_call": first_flag,
    }


def _mean(xs: list[float | None]) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(statistics.mean(xs), 1) if xs else None


def write(raw_path: Path) -> Path:
    batch = json.loads(Path(raw_path).read_text())
    runs = [run_metrics(r["run_id"]) for r in batch["runs"]]
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in runs:
        groups[(r["scenario"], r["profile"])].append(r)

    cols = [("n", lambda rs: len(rs)),
            ("correct", lambda rs: f"{sum(r['correct'] for r in rs)}/{len(rs)}"),
            ("status", lambda rs: ",".join(sorted({r["status"] for r in rs}))),
            ("steps", lambda rs: _mean([r["steps"] for r in rs])),
            ("ctx tok total", lambda rs: _mean([r["agent_ctx_tokens_total"] for r in rs])),
            ("ctx tok peak", lambda rs: _mean([r["agent_ctx_tokens_peak"] for r in rs])),
            ("prefill tok", lambda rs: _mean([r["agent_prompt_eval_total"] for r in rs])),
            ("agent model s", lambda rs: _mean([r["agent_model_s"] for r in rs])),
            ("wall s", lambda rs: _mean([r["wall_s"] for r in rs])),
            ("SD calls", lambda rs: _mean([r["sd_calls"] for r in rs])),
            ("SD s", lambda rs: _mean([r["sd_s"] for r in rs])),
            ("local summ s", lambda rs: _mean([r["local_summarize_s"] for r in rs])),
            ("nudges", lambda rs: _mean([r["nudges"] for r in rs])),
            ("prodsim calls", lambda rs: _mean([r["prodsim_calls"] for r in rs])),
            ("calls after 1st 5xx", lambda rs: _mean([r["calls_after_first_failure"] for r in rs]))]

    lines = [f"# Bench results {batch['stamp']}", "",
             "Means over repeats. `ctx tok` = cl100k tokens sent to the agent model (summed over "
             "calls / max single call). `prefill tok` = Ollama prompt_eval_count (KV-cache hits "
             "excluded): the compute actually spent. `SD` = ScaleDown API.", ""]
    for scenario in sorted({k[0] for k in groups}):
        lines += [f"## {scenario}", "", "| profile | " + " | ".join(c for c, _ in cols) + " |",
                  "|---|" + "---|" * len(cols)]
        for (s, profile), rs in sorted(groups.items()):
            if s == scenario:
                lines.append(f"| {profile} | " + " | ".join(
                    "–" if (v := f(rs)) is None else str(v) for _, f in cols) + " |")
        flags = defaultdict(list)
        for (s, profile), rs in groups.items():
            if s == scenario:
                for r in rs:
                    for det, at in r["first_flag_at_tool_call"].items():
                        flags[det].append(f"{profile}:{at}")
        if flags:
            lines += ["", "First non-progress flag (p≥0.6) by detector, as profile:tool_call — "
                          + "; ".join(f"**{d}** {', '.join(v)}" for d, v in sorted(flags.items()))]
        lines.append("")

    out_md = Path("results") / f"{batch['stamp']}.md"
    out_md.write_text("\n".join(lines))
    out_md.with_suffix(".json").write_text(json.dumps(runs, indent=1, default=str))
    print("\n".join(lines))
    print(f"\nwrote {out_md}")
    return out_md


if __name__ == "__main__":
    write(Path(sys.argv[1]))
