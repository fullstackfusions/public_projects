"""Component bench (no agent, no LLM): what does each context reducer do to real tool output?

For every scenario, fetch the bulky tool outputs an investigation would plausibly pull,
then measure four treatments on identical bytes:
  raw | log_fold | sd_compress | log_fold -> sd_compress
and check whether the evidence that grading depends on survives each one.

    docker compose --profile bench run --rm bench python -m oncall.bench.compress_bench
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import httpx

from oncall import telemetry
from oncall.agent.middleware import fold_logs
from oncall.config import settings

# (tool, path, params, compression query): what an engineer would ask of that output.
PROBES = {
    "db-pool-exhaustion": [
        ("query_logs", "/logs", {"service": "payments-api"}, "why are payments requests failing"),
        ("query_logs", "/logs", {"service": "checkout-api"}, "which upstream is failing"),
        ("search_runbooks", "/runbooks/search", {"q": "remaining connection slots reserved"},
         "how to diagnose postgres connection exhaustion"),
    ],
    "bad-feature-flag": [
        ("query_logs", "/logs", {"service": "search-api"}, "why is search latency high"),
        ("get_k8s_events", "/k8s/events", {}, "reranker pod failures"),
        ("search_runbooks", "/runbooks/search", {"q": "search latency reranker"},
         "what causes reranker overload"),
    ],
    "red-herring-drift": [
        ("query_logs", "/logs", {"service": "auth-api"}, "why are SSO logins failing"),
        ("get_k8s_events", "/k8s/events", {}, "recent changes to DNS or auth"),
    ],
    "log-flood": [
        ("query_logs", "/logs", {"service": "inventory-consumer", "limit": 2000},
         "why is consumer lag growing"),
        ("query_logs", "/logs", {"service": "kafka", "limit": 2000}, "consumer group rebalances"),
    ],
}

# Evidence strings that must survive for the agent to be able to reach the right answer.
EVIDENCE = {
    "db-pool-exhaustion": ["remaining connection slots", "upstream payments-api", "QueuePool limit",
                           "max_connections"],
    "bad-feature-flag": ["context deadline exceeded", "OOMKilled", "semantic_rerank"],
    "red-herring-drift": ["no such host", "ConfigMap kube-system/coredns"],
    "log-flood": ["max.poll.interval.ms", "Preparing to rebalance", "records=5000"],
}


def _fetch(scenario_id: str, path: str, params: dict) -> str:
    r = httpx.get(f"{settings().prodsim_url}{path}", params=params,
                  headers={"X-Scenario": scenario_id}, timeout=30)
    r.raise_for_status()
    ct = r.headers.get("content-type", "")
    return r.text if ct.startswith("text/") else json.dumps(r.json(), indent=1)


def _measure(text: str, query: str, treatment: str) -> dict:
    t0 = time.perf_counter()
    if treatment == "raw":
        out = text
    elif treatment == "log_fold":
        out = fold_logs(text) if text.startswith("# logs") else text
    else:
        src = fold_logs(text) if treatment == "fold+sd_compress" and text.startswith("# logs") \
            else text
        resp = telemetry.scaledown_client().compress(src, query)
        out = resp.get("compressed_prompt") if resp.get("successful") else src
    return {"tokens": telemetry.count_tokens(out), "ms": (time.perf_counter() - t0) * 1000,
            "out": out}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3, help="ScaleDown latency samples per item")
    ap.add_argument("--out", default="results/compress_bench.json")
    args = ap.parse_args()
    treatments = ["raw", "log_fold", "sd_compress", "fold+sd_compress"]
    rows = []
    for scenario_id, probes in PROBES.items():
        for tool, path, params, query in probes:
            text = _fetch(scenario_id, path, params)
            row = {"scenario": scenario_id, "tool": tool, "params": params, "query": query}
            for t in treatments:
                samples = [_measure(text, query, t) for _ in range(1 if t in ("raw", "log_fold")
                                                                    else args.repeats)]
                out = samples[0]["out"]
                row[t] = {
                    "tokens": samples[0]["tokens"],
                    "ms_median": round(statistics.median(s["ms"] for s in samples), 1),
                    "evidence_kept": [e for e in EVIDENCE[scenario_id] if e in text and e in out],
                    "evidence_in_raw": [e for e in EVIDENCE[scenario_id] if e in text],
                }
            rows.append(row)
            print(f"{scenario_id:20} {tool:16} " + "  ".join(
                f"{t}={row[t]['tokens']:>6}tok/{len(row[t]['evidence_kept'])}"
                f"of{len(row[t]['evidence_in_raw'])}" for t in treatments), flush=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(rows, indent=1))
    _markdown(rows, Path(args.out).with_suffix(".md"))
    print(f"wrote {args.out}")


def _markdown(rows: list[dict], path: Path) -> None:
    treatments = ["raw", "log_fold", "sd_compress", "fold+sd_compress"]
    lines = ["# Component bench: tool-output reduction", "",
             "Tokens are cl100k. `evidence` = grading-relevant strings present in the raw output "
             "that survive the treatment. Latency is median of ScaleDown calls.", "",
             "| scenario | tool | " + " | ".join(treatments) + " |",
             "|---|---|" + "---|" * len(treatments)]
    for r in rows:
        cells = []
        for t in treatments:
            c = r[t]
            pct = 100 * (1 - c["tokens"] / r["raw"]["tokens"]) if r["raw"]["tokens"] else 0
            ev = f"{len(c['evidence_kept'])}/{len(c['evidence_in_raw'])}"
            lat = f", {c['ms_median']:.0f}ms" if "sd" in t else ""
            cells.append(f"{c['tokens']:,} tok ({-pct:+.0f}%, ev {ev}{lat})"
                         if t != "raw" else f"{c['tokens']:,} tok (ev {ev})")
        lines.append(f"| {r['scenario']} | {r['tool']} | " + " | ".join(cells) + " |")
    path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
