"""Frontier models vs ScaleDown on the same context-management inputs.

Tests the blog's headline claim (ScaleDown is far cheaper than frontier models for
narrow context tasks) on our own inputs, with quality measured against labels:

  compress  : LogHub windows + runbook pages, query-aware.  Quality = abnormal-template
              recall (LogHub labels) / evidence strings kept (runbooks).
  classify  : 21 hand-labeled loop/drift/progressing trajectories. Quality = accuracy.
  summarize : investigation transcripts built from prodsim tool outputs. Quality = are
              the root-cause facts (scenario keyword groups) still in the summary?

Costs: OpenAI from returned `usage` x list price; ScaleDown classify from its own
`usage.cost`; ScaleDown compress/summarize from input tokens x list price. Prices are
in PRICES with their source; re-check before publishing.

    # estimate only (default):
    docker compose --profile bench run --rm --no-deps bench python -m oncall.bench.frontier_bench
    # spend money:
    docker compose --profile bench run --rm --no-deps bench \
        python -m oncall.bench.frontier_bench --execute
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

import httpx

from oncall import telemetry
from oncall.agent.guard import CRITERIA, LABELS
from oncall.agent.middleware import fold_logs
from oncall.bench import loghub_bench
from oncall.bench.trajectories import labeled_digests
from oncall.config import settings
from oncall.prodsim import runbooks
from oncall.prodsim.scenarios import SCENARIOS

# USD per 1M tokens (input, output). Looked up 2026-10-13; aggregator sources, see README.
PRICES = {
    "gpt-5.5": (5.00, 30.00),
    "gpt-5.4-mini": (0.75, 4.50),
    "gpt-5.4-nano": (0.20, 1.25),
    "scaledown:compress": (0.05, 0.0),
    "scaledown:classify": (0.05, 0.0),
    "scaledown:summarize": (0.04, 0.0),  # catalogs disagree (0.02-0.04); conservative
}
OPENAI_MODELS = ["gpt-5.4-nano", "gpt-5.4-mini", "gpt-5.5"]

COMPRESS_PROMPT = (
    "You are a context compressor for an AI agent. From the CONTEXT, return only the lines or "
    "passages relevant to the QUESTION, copied verbatim and in their original order. Do not "
    "paraphrase, summarize, explain or add anything.\n\nQUESTION: {q}\n\nCONTEXT:\n{c}")
SUMMARY_PROMPT = (
    "This summary replaces an AI agent's conversation history, and the agent will continue "
    "working from it. Keep every concrete identifier (deploy ids, versions, error strings, "
    "config keys, service names). Sections: SESSION INTENT, SUMMARY, ARTIFACTS, NEXT STEPS."
    "\n\n{c}")
CLASSIFY_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["label"],
    "properties": {"label": {"type": "string", "enum": list(LABELS)}},
}


class OpenAI:
    def __init__(self, key: str) -> None:
        self.http = httpx.Client(base_url="https://api.openai.com/v1", timeout=300,
                                 headers={"Authorization": f"Bearer {key}"})

    def chat(self, model: str, prompt: str, schema: dict | None = None) -> tuple[str, dict, float]:
        body: dict[str, Any] = {"model": model, "messages": [{"role": "user", "content": prompt}],
                                "reasoning_effort": "none"}
        if schema:
            body["response_format"] = {"type": "json_schema", "json_schema": {
                "name": "out", "strict": True, "schema": schema}}
        t0 = time.perf_counter()
        r = self.http.post("/chat/completions", json=body)
        if r.status_code == 400 and "reasoning_effort" in r.text:
            body["reasoning_effort"] = "minimal"  # older models lack "none"
            r = self.http.post("/chat/completions", json=body)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"] or "", data["usage"], \
            (time.perf_counter() - t0) * 1000


def cost(model_key: str, tokens_in: int, tokens_out: int) -> float:
    p_in, p_out = PRICES[model_key]
    return (tokens_in * p_in + tokens_out * p_out) / 1e6


# --- inputs -------------------------------------------------------------------------------


def compress_inputs(lines: int) -> list[dict]:
    items = []
    for system, query in loghub_bench.SYSTEMS.items():
        raw, rows = loghub_bench.load(system, Path("results/data/loghub"))
        raw, rows = raw[:lines], rows[:lines]
        items.append({"name": f"loghub:{system}", "text": "\n".join(raw), "query": query,
                      "rows": rows})
    for q, must in [("remaining connection slots reserved postgres",
                     ["pool_size", "workers", "PgBouncer"]),
                    ("SSO login failures no such host coredns",
                     ["stub", "ConfigMap kube-system/coredns", "idp.internal"]),
                    ("kafka consumer rebalance poll timeout",
                     ["max.poll.records", "max.poll.interval.ms"])]:
        text = "\n\n".join(r["content"] for r in runbooks.search(q))
        items.append({"name": f"runbooks:{q[:24]}", "text": text, "query": q, "must": must})
    return items


def transcripts() -> list[dict]:
    """A plausible mid-investigation history per scenario, from real prodsim outputs."""
    from fastapi.testclient import TestClient

    from oncall.prodsim.app import app

    c = TestClient(app)
    plans = {
        "db-pool-exhaustion": [("/logs", {"service": "checkout-api", "level": "WARN"}),
                               ("/logs", {"service": "payments-api", "level": "WARN"}),
                               ("/deploys", {"service": "payments-api"}),
                               ("/runbooks/search", {"q": "remaining connection slots"})],
        "bad-feature-flag": [("/logs", {"service": "search-api", "level": "WARN"}),
                             ("/k8s/events", {"namespace": "search"}),
                             ("/logs", {"service": "flagd"}),
                             ("/runbooks/search", {"q": "reranker latency"})],
        "red-herring-drift": [("/logs", {"service": "edge-gateway", "level": "WARN"}),
                              ("/logs", {"service": "auth-api", "level": "WARN"}),
                              ("/k8s/events", {"namespace": "kube-system"}),
                              ("/runbooks/search", {"q": "no such host dns"})],
        "log-flood": [("/logs", {"service": "inventory-consumer", "level": "WARN"}),
                      ("/logs", {"service": "kafka"}),
                      ("/deploys", {"service": "inventory-consumer"})],
    }
    out = []
    for scenario_id, calls in plans.items():
        s = SCENARIOS[scenario_id]
        parts = [f"<user>{s.alert}</user>"]
        for path, params in calls:
            body = c.get(path, params=params, headers={"X-Scenario": scenario_id}).text
            body = fold_logs(body) if body.startswith("# logs") else body
            parts.append(f"<assistant>calling {path} {json.dumps(params)}</assistant>")
            parts.append(f"<tool>{body}</tool>")
        out.append({"name": scenario_id, "text": "\n".join(parts), "groups": s.keyword_groups})
    return out


# --- scoring --------------------------------------------------------------------------------


def score_compress(item: dict, out: str) -> str:
    if "rows" in item:
        kept, total = loghub_bench.recall(out, item["rows"], abnormal_only=True)
        return f"{kept}/{total}"
    return f"{sum(m in out for m in item['must'])}/{len(item['must'])}"


def score_summary(item: dict, out: str) -> str:
    low = out.lower()
    hits = sum(any(t.lower() in low for t in g) for g in item["groups"])
    return f"{hits}/{len(item['groups'])}"


# --- runner ---------------------------------------------------------------------------------


def estimate(comp: list[dict], trans: list[dict], digests: list) -> float:
    total = 0.0
    for m in OPENAI_MODELS:
        tin = sum(telemetry.count_tokens(COMPRESS_PROMPT.format(q=i["query"], c=i["text"]))
                  for i in comp)
        tin += sum(telemetry.count_tokens(SUMMARY_PROMPT.format(c=t["text"])) for t in trans)
        tin += sum(telemetry.count_tokens(d) + 200 for _, d in digests)
        tout = int(0.3 * sum(telemetry.count_tokens(i["text"]) for i in comp)) + 600 * len(trans)
        c = cost(m, tin, tout)
        print(f"  {m:14} ~{tin:>9,} in / ~{tout:>8,} out tokens -> ~${c:.2f}")
        total += c
    return total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="actually call the APIs")
    ap.add_argument("--lines", type=int, default=600, help="LogHub window per system")
    ap.add_argument("--out", default="results/frontier_bench.json")
    args = ap.parse_args()
    comp, trans, digests = compress_inputs(args.lines), transcripts(), labeled_digests()
    print(f"inputs: {len(comp)} compress, {len(trans)} summarize, {len(digests)} classify")
    est = estimate(comp, trans, digests)
    print(f"estimated OpenAI total (upper-ish bound): ~${est:.2f}")
    if not args.execute:
        print("dry run; pass --execute to spend it")
        return

    oa = OpenAI(settings().openai_api_key or "")
    sd = telemetry.scaledown_client()
    results: dict[str, list] = {"compress": [], "summarize": [], "classify": []}

    for item in comp:
        sd_r = sd.compress(item["text"], item["query"])
        out = sd_r.get("compressed_prompt") if sd_r.get("successful") else item["text"]
        tin = telemetry.count_tokens(item["text"])
        row = {"input": item["name"], "in_tokens": tin, "scaledown": {
            "out_tokens": telemetry.count_tokens(out), "quality": score_compress(item, out),
            "ms": sd_r.get("latency_ms"), "usd": cost("scaledown:compress", tin, 0),
            "identical": out == item["text"]}}
        for m in OPENAI_MODELS:
            text, usage, ms = oa.chat(m, COMPRESS_PROMPT.format(q=item["query"], c=item["text"]))
            row[m] = {"out_tokens": telemetry.count_tokens(text),
                      "quality": score_compress(item, text), "ms": round(ms),
                      "usd": cost(m, usage["prompt_tokens"], usage["completion_tokens"])}
        results["compress"].append(row)
        print("compress", item["name"], {k: (v["quality"], v["out_tokens"]) for k, v in row.items()
                                          if isinstance(v, dict)}, flush=True)

    for item in trans:
        tin = telemetry.count_tokens(item["text"])
        t0 = time.perf_counter()
        summary = sd.summarize(item["text"], max_tokens=1024)
        row = {"input": item["name"], "in_tokens": tin, "scaledown": {
            "out_tokens": telemetry.count_tokens(summary), "quality": score_summary(item, summary),
            "ms": round((time.perf_counter() - t0) * 1000),
            "usd": cost("scaledown:summarize", tin, 0)}}
        for m in OPENAI_MODELS:
            text, usage, ms = oa.chat(m, SUMMARY_PROMPT.format(c=item["text"]))
            row[m] = {"out_tokens": telemetry.count_tokens(text),
                      "quality": score_summary(item, text), "ms": round(ms),
                      "usd": cost(m, usage["prompt_tokens"], usage["completion_tokens"])}
        results["summarize"].append(row)
        print("summarize", item["name"], {k: v["quality"] for k, v in row.items()
                                           if isinstance(v, dict)}, flush=True)

    question = {"type": "choice", "criteria": CRITERIA,
                "instructions": "Judge only the agent's recent behaviour against the alert."}
    clf_prompt = ("Classify the agent's recent behaviour. Labels:\n"
                  + "\n".join(f"- {k}: {v}" for k, v in CRITERIA.items()) + "\n\n{d}")
    per_model: dict[str, list] = {"scaledown": []}
    for label, d in digests:
        t0 = time.perf_counter()
        ans = sd.classify(d, {"trajectory": question})
        a = ans["answers"]["trajectory"]
        per_model["scaledown"].append({"gold": label, "pred": a["choice"],
                                       "ms": (time.perf_counter() - t0) * 1000,
                                       "usd": (ans.get("usage") or {}).get("cost", 0.0)})
        for m in OPENAI_MODELS:
            text, usage, ms = oa.chat(m, clf_prompt.format(d=d), schema=CLASSIFY_SCHEMA)
            per_model.setdefault(m, []).append({
                "gold": label, "pred": json.loads(text)["label"], "ms": ms,
                "usd": cost(m, usage["prompt_tokens"], usage["completion_tokens"])})
    for m, preds in per_model.items():
        acc = sum(p["gold"] == p["pred"] for p in preds)
        by_label = {lab: f"{sum(p['gold'] == p['pred'] for p in preds if p['gold'] == lab)}/"
                         f"{sum(p['gold'] == lab for p in preds)}" for lab in LABELS}
        results["classify"].append({
            "model": m, "accuracy": f"{acc}/{len(preds)}", "by_label": by_label,
            "ms_median": round(statistics.median(p["ms"] for p in preds)),
            "usd_total": sum(p["usd"] for p in preds), "preds": preds})
        print("classify", m, f"{acc}/{len(preds)}", by_label, flush=True)

    Path(args.out).write_text(json.dumps(results, indent=1, default=str))
    write_markdown(results, Path(args.out).with_suffix(".md"))
    print(f"wrote {args.out}")


def write_markdown(results: dict, path: Path) -> None:
    models = ["scaledown", *OPENAI_MODELS]
    md = ["# Frontier vs ScaleDown on context-management tasks", "",
          "Same inputs for every model. Cost from returned usage x list price (see PRICES). "
          "Quality: compress = abnormal LogHub templates (or runbook facts) kept verbatim; "
          "summarize = root-cause keyword groups retained; classify = accuracy on 21 "
          "hand-labeled trajectories.", ""]
    for task in ("compress", "summarize"):
        md += [f"## {task}", "", "| input | in tok | " + " | ".join(models) + " |",
               "|---|---|" + "---|" * len(models)]
        totals = {m: [0.0, 0.0] for m in models}
        for r in results[task]:
            cells = []
            for m in models:
                c = r[m]
                totals[m][0] += c["usd"]
                totals[m][1] += c["ms"] or 0
                cells.append(f"{c['quality']} · {c['out_tokens']:,} tok · {c['ms'] or 0:,.0f}ms"
                             + (" · identical" if c.get("identical") else ""))
            md.append(f"| {r['input']} | {r['in_tokens']:,} | " + " | ".join(cells) + " |")
        md.append("| **total $ / time** | | " + " | ".join(
            f"**${totals[m][0]:.4f}** / {totals[m][1] / 1000:.0f}s" for m in models) + " |")
        md.append("")
    md += ["## classify (loop / drift / progressing)", "",
           "| model | accuracy | progressing | looping | drifting | median ms | total $ |",
           "|---|---|---|---|---|---|---|"]
    for r in results["classify"]:
        b = r["by_label"]
        md.append(f"| {r['model']} | {r['accuracy']} | {b['progressing']} | {b['looping']} | "
                  f"{b['drifting']} | {r['ms_median']:,} | ${r['usd_total']:.5f} |")
    path.write_text("\n".join(md) + "\n")


if __name__ == "__main__":
    main()
