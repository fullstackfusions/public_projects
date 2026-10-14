"""Capture dashboard screenshots for the write-up (headless Chromium via Playwright).

    # whole page for the latest run
    uv run --no-project --with playwright==1.55.0 python scripts/screenshots.py
    # one panel of one run, only some event kinds, oldest first
    uv run --no-project --with playwright==1.55.0 python scripts/screenshots.py \
        --run <id> --element timeline-panel --kinds model_call,guard_check,guard_nudge \
        --order asc --name guard-verdicts
    # two runs overlaid
    uv run --no-project --with playwright==1.55.0 python scripts/screenshots.py \
        --compare <id1>,<id2> --element compare-panel --name log-flood-ledger

First time only: `uv run --no-project --with playwright==1.55.0 playwright install chromium`.
Elements: detail (run panel + chart + timeline), summary-panel, chart-ledger, timeline-panel,
compare-panel (default: full page).
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--run", help="run id (default: most recent)")
    ap.add_argument("--compare", help="comma-separated run ids to overlay")
    ap.add_argument("--element", help="panel id to capture instead of the full page")
    ap.add_argument("--kinds", help="only these timeline event kinds, comma-separated")
    ap.add_argument("--order", choices=["asc", "desc"], default="desc")
    ap.add_argument("--steps", help="model-call window, e.g. 11-16")
    ap.add_argument("--wide", action="store_true", help="hide sidebar; timeline full width")
    ap.add_argument("--hide", help="panel ids to hide, comma-separated (e.g. chart-ledger)")
    ap.add_argument("--title", help="timeline panel heading")
    ap.add_argument("--schemes", default="light,dark")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--name", help="file name stem")
    ap.add_argument("--out", default="results/screenshots")
    args = ap.parse_args()

    query: dict[str, str] = {"full": "1"}
    if args.compare:
        query["compare"] = args.compare
        stem = args.name or "compare"
    else:
        runs = json.load(urllib.request.urlopen(f"{args.base}/api/runs?limit=100"))
        run = next(r for r in runs if r["id"].startswith(args.run)) if args.run else runs[0]
        query["run"] = run["id"]
        stem = args.name or f"{run['scenario']}-{run['profile']}-{run['status']}"
    if args.kinds:
        query["kinds"] = args.kinds
    if args.order == "asc":
        query["order"] = "asc"
    if args.steps:
        query["steps"] = args.steps
    if args.wide:
        query["wide"] = "1"
    if args.hide:
        query["hide"] = args.hide
    if args.title:
        query["title"] = args.title
    url = f"{args.base}/?{urllib.parse.urlencode(query)}"

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for scheme in args.schemes.split(","):
            page = browser.new_page(viewport={"width": args.width, "height": 1000},
                                    color_scheme=scheme, device_scale_factor=2)
            page.goto(url)
            target = f"#{args.element}" if args.element else "body"
            page.wait_for_selector("#compare-panel svg" if args.compare else "#tl .ev")
            page.wait_for_timeout(2000)  # let the SSE replay finish filling the timeline
            path = out / (f"{stem}.png" if scheme == "light" else f"{stem}-{scheme}.png")
            page.locator(target).screenshot(path=str(path))
            print(f"wrote {path}")
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
