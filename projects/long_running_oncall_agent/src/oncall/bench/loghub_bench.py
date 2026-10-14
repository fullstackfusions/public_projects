"""Component bench on real public logs: LogHub (logpai/loghub, 2k-line samples per system).

LogHub's structured files label every line with its ground-truth event template, so
"did the reducer keep the evidence?" becomes a measurable recall instead of a judgment:

  abnormal recall = fraction of distinct WARN/ERROR/FATAL event templates in the window
                    for which at least one line survives verbatim in the reduced output.

Reducers: raw | log_fold | sd_compress (query-aware) | log_fold -> sd_compress.

    docker compose --profile bench run --rm --no-deps bench python -m oncall.bench.loghub_bench

Dataset: He et al., "Loghub: A Large Collection of System Log Datasets for AI-driven Log
Analytics", ISSRE 2023. https://github.com/logpai/loghub
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import time
from pathlib import Path

import httpx

from oncall import telemetry
from oncall.agent.middleware import fold_logs

BASE = "https://raw.githubusercontent.com/logpai/loghub/master"
ABNORMAL = {"WARN", "WARNING", "ERROR", "FATAL", "SEVERE", "error"}

# system -> the question an on-call engineer would ask of that log.
SYSTEMS = {
    "OpenStack": "Which requests or instances failed or produced warnings, and why?",
    "HDFS": "Are there any block or datanode problems? Which warnings occurred?",
    "Hadoop": "Why did the MapReduce job fail? Which errors occurred and in which component?",
    "BGL": "Which hardware or kernel failures occurred on the nodes?",
    "Apache": "What errors is the web server reporting?",
    "Zookeeper": "Why are the quorum peers losing connections? Which errors occurred?",
}


def load(system: str, cache: Path) -> tuple[list[str], list[dict]]:
    """Raw lines and their aligned structured rows (same order, same count)."""
    cache.mkdir(parents=True, exist_ok=True)
    out = []
    for suffix in ("log", "log_structured.csv"):
        f = cache / f"{system}_2k.{suffix}"
        if not f.exists():
            r = httpx.get(f"{BASE}/{system}/{system}_2k.{suffix}", timeout=60)
            r.raise_for_status()
            f.write_bytes(r.content)
        out.append(f.read_text(errors="replace"))
    raw_lines = out[0].splitlines()
    rows = list(csv.DictReader(io.StringIO(out[1])))
    if len(raw_lines) != len(rows):
        raise ValueError(f"{system}: {len(raw_lines)} raw lines vs {len(rows)} labeled rows")
    return raw_lines, rows


def recall(output: str, rows: list[dict], abnormal_only: bool) -> tuple[int, int]:
    want: dict[str, list[str]] = {}
    for r in rows:
        if abnormal_only and r["Level"] not in ABNORMAL:
            continue
        want.setdefault(r["EventId"], []).append(r["Content"])
    kept = sum(1 for contents in want.values() if any(c in output for c in contents))
    return kept, len(want)


def reduce(text: str, query: str, treatment: str) -> tuple[str, float, dict]:
    t0 = time.perf_counter()
    meta: dict = {}
    if treatment == "raw":
        out = text
    elif treatment == "log_fold":
        out = fold_logs(text)
    else:
        src = fold_logs(text) if treatment.startswith("fold") else text
        resp = telemetry.scaledown_client().compress(src, query)
        meta = {"successful": resp.get("successful"),
                "sd_reported_in": resp.get("original_prompt_tokens"),
                "sd_reported_out": resp.get("compressed_prompt_tokens"),
                "byte_identical": resp.get("compressed_prompt") == src}
        out = resp.get("compressed_prompt") if resp.get("successful") else src
    return out, (time.perf_counter() - t0) * 1000, meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", type=int, default=600, help="window size per system")
    ap.add_argument("--systems", nargs="+", default=list(SYSTEMS))
    ap.add_argument("--out", default="results/loghub_bench.json")
    args = ap.parse_args()
    cache = Path("results/data/loghub")
    treatments = ["raw", "log_fold", "sd_compress", "fold+sd_compress"]
    rows_out = []
    for system in args.systems:
        raw_lines, rows = load(system, cache)
        raw_lines, rows = raw_lines[: args.lines], rows[: args.lines]
        text = "\n".join(raw_lines)
        query = SYSTEMS[system]
        result = {"system": system, "lines": len(raw_lines), "query": query,
                  "gt_templates": len({r["EventId"] for r in rows})}
        for t in treatments:
            out, ms, meta = reduce(text, query, t)
            ab_kept, ab_total = recall(out, rows, abnormal_only=True)
            all_kept, all_total = recall(out, rows, abnormal_only=False)
            result[t] = {"tokens": telemetry.count_tokens(out), "ms": round(ms),
                         "abnormal_recall": [ab_kept, ab_total],
                         "template_recall": [all_kept, all_total], **meta}
            if t == "log_fold":
                result[t]["fold_groups"] = len(out.splitlines()) - 1
        rows_out.append(result)
        print(f"{system:10} gt_templates={result['gt_templates']:>3} " + "  ".join(
            f"{t}={result[t]['tokens']:>6}tok ab={result[t]['abnormal_recall'][0]}/"
            f"{result[t]['abnormal_recall'][1]}" for t in treatments), flush=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(rows_out, indent=1))
    md = ["# LogHub component bench", "",
          f"Window: first {args.lines} lines per system. Tokens: cl100k. `abnormal` = distinct "
          "WARN/ERROR/FATAL ground-truth templates with at least one line kept verbatim. "
          "`identical` = ScaleDown returned the input unchanged while reporting success.", "",
          "| system | GT templates | " + " | ".join(treatments) + " |",
          "|---|---|" + "---|" * len(treatments)]
    for r in rows_out:
        cells = []
        for t in treatments:
            c = r[t]
            cut = 100 * (1 - c["tokens"] / r["raw"]["tokens"])
            ab = "{}/{}".format(*c["abnormal_recall"])
            extra = f", {c['ms']}ms" if "sd" in t else ""
            extra += ", identical" if c.get("byte_identical") else ""
            cells.append(f"{c['tokens']:,} tok" + (f" ({-cut:+.0f}%)" if t != "raw" else "")
                         + f", abnormal {ab}{extra}")
        md.append(f"| {r['system']} | {r['gt_templates']} | " + " | ".join(cells) + " |")
    Path(args.out).with_suffix(".md").write_text("\n".join(md) + "\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
