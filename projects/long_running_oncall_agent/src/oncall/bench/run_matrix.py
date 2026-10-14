"""End-to-end bench: scenarios x profiles x repeats, through the real production path.

Runs are submitted to the API one at a time (Ollama serves one request at a time, so
concurrency would only add queueing noise to latency) and awaited to a terminal state.
The run ids are written to results/raw/<stamp>.json; `report` aggregates them.

    docker compose --profile bench run --rm bench \
        python -m oncall.bench.run_matrix --profiles baseline scaledown_fold --repeats 2
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from oncall.bench import report
from oncall.config import settings
from oncall.db import TERMINAL_STATUSES
from oncall.prodsim.scenarios import SCENARIOS


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", nargs="+", default=list(SCENARIOS))
    ap.add_argument("--profiles", nargs="+", default=["baseline", "scaledown", "scaledown_fold"])
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--timeout-s", type=int, default=3600)
    args = ap.parse_args()

    api = httpx.Client(base_url=settings().api_url, timeout=30)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    raw = Path("results/raw") / f"{stamp}.json"
    raw.parent.mkdir(parents=True, exist_ok=True)
    plan = [(s, p, i) for i in range(args.repeats) for s in args.scenarios for p in args.profiles]
    done: list[dict] = []
    print(f"{len(plan)} runs planned -> {raw}", flush=True)

    for n, (scenario, profile, rep) in enumerate(plan, 1):
        run = api.post("/api/runs", json={"scenario": scenario, "profile": profile}).json()
        t0 = time.time()
        while True:
            time.sleep(5)
            cur = api.get(f"/api/runs/{run['id']}").json()
            if cur["status"] in TERMINAL_STATUSES:
                break
            if time.time() - t0 > args.timeout_s:
                print(f"  timeout waiting for {run['id']}", flush=True)
                break
        done.append({"run_id": run["id"], "scenario": scenario, "profile": profile, "rep": rep})
        raw.write_text(json.dumps({"stamp": stamp, "runs": done}, indent=1))
        grade = cur.get("grade") or {}
        print(f"[{n}/{len(plan)}] {scenario:20} {profile:16} -> {cur['status']:16} "
              f"correct={grade.get('correct')} {time.time() - t0:.0f}s", flush=True)

    report.write(raw)


if __name__ == "__main__":
    main()
