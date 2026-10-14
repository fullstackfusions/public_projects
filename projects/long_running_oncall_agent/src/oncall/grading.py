"""Deterministic grading against scenario ground truth, plus prodsim access-log stats.

Grading is keyword-based on purpose: it is reproducible and cheap, and its failure
mode (a correct report phrased with none of the expected terms) is visible in the
stored report, unlike an LLM judge's.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

import redis

from oncall.prodsim.scenarios import scenario


def grade(scenario_id: str, report: dict[str, Any] | None) -> dict[str, Any]:
    s = scenario(scenario_id)
    if not report:
        return {"correct": False, "reason": "no report submitted", "groups_hit": []}
    text = str(report.get("root_cause", "")).lower()
    hits = [any(term.lower() in text for term in group) for group in s.keyword_groups]
    missing = [list(g) for g, h in zip(s.keyword_groups, hits, strict=True) if not h]
    return {
        "correct": all(hits),
        "groups_hit": hits,
        "expected": s.root_cause,
        "reason": "all keyword groups present" if all(hits) else f"missing groups: {missing}",
    }


def access_stats(r: redis.Redis, run_id: str) -> dict[str, Any]:
    """What the agent actually did, from prodsim's side of the wire."""
    entries = [json.loads(x) for x in r.lrange(f"prodsim:access:{run_id}", 0, -1)]
    calls = [(e["endpoint"], json.dumps(e["params"], sort_keys=True)) for e in entries]
    failed = [i for i, e in enumerate(entries) if e["status"] >= 500]
    repeat_counts = Counter(calls)
    return {
        "prodsim_calls": len(entries),
        "failed_calls": len(failed),
        # 1-based index of the first 5xx (the loop trap's onset) and calls made after it.
        "first_failure_call": failed[0] + 1 if failed else None,
        "calls_after_first_failure": len(entries) - failed[0] - 1 if failed else 0,
        "max_identical_calls": max(repeat_counts.values(), default=0),
        "endpoints": dict(Counter(e["endpoint"] for e in entries)),
        "bytes_returned": sum(e["bytes"] for e in entries),
    }
