"""
Runs the graphs back-to-back and prints a comparison table.

Three configurations:
  baseline       — no compression
  rule-based     — SmartCrusher + CodeCompressor (deterministic)
  kompress       — rule-based + Kompress ML prose compressor (opt-in escalation)

Usage:
  python compare.py              # run all three, print table
  python compare.py --save       # also write results.json
  python compare.py --baseline-only
  python compare.py --no-kompress  # skip the Kompress run (rule-based only)
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

# Repo root = three levels up from this file (…/public_projects).
# Each config runs in its OWN subprocess: Headroom caches a module-level
# compression pipeline that latches the first kompress_model it sees, so
# running "disabled" then "enabled" in one process silently keeps Kompress
# off. Process isolation is the only reliable way to measure both configs.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PKG = "projects.local_first_compression_layer"


def _run_config(module: str) -> dict:
    """Run a runner module in a fresh subprocess and return its result JSON."""
    with tempfile.NamedTemporaryFile("r", suffix=".json", delete=False) as tf:
        out_path = tf.name
    subprocess.run(
        [sys.executable, "-m", f"{_PKG}.{module}", "--out", out_path],
        cwd=_REPO_ROOT,
        check=True,
    )
    return json.loads(Path(out_path).read_text())


def _delta_pct(before: float, after: float) -> str:
    if before == 0:
        return "-"
    p = (after - before) / before * 100
    sign = "+" if p > 0 else ""
    return f"{sign}{p:.1f}%"


def _delta_abs(before: float, after: float) -> str:
    d = after - before
    sign = "+" if d > 0 else ""
    return f"{sign}{int(d)}"


def _reduction_pct(run: dict) -> float:
    """Headroom-reported context reduction (tokens_saved / tokens_before), as %."""
    saved = run.get("tokens_saved", 0)
    before = run.get("raw_token_estimate", 0)
    return round(saved / before * 100, 1) if before else 0.0


def print_table(baseline: dict, runs: list[dict]):
    try:
        from rich.console import Console
        from rich import box
        _rich_table(Console(), baseline, runs, box)
    except ImportError:
        _plain_table(baseline, runs)


def _rich_table(console, baseline: dict, runs: list[dict], box):
    from rich.table import Table

    def color(val: str) -> str:
        if val.startswith("-"):
            return f"[green]{val}[/green]"
        if val.startswith("+") and val != "+0":
            return f"[red]{val}[/red]"
        return val

    labels = {"with_headroom": "Rule-based", "with_kompress": "+ Kompress (ML)"}

    t = Table(title=f"Headroom vs Baseline  |  model: {baseline['model']}",
              box=box.ROUNDED, show_lines=True)
    t.add_column("Metric", style="cyan", min_width=30)
    t.add_column("Baseline", justify="right")
    for r in runs:
        t.add_column(labels.get(r.get("run", ""), r.get("run", "")), justify="right")

    metric_rows = [
        ("Send token estimate (tiktoken)", "raw_token_estimate", "send_token_estimate"),
        ("Prompt tokens (Ollama)",         "prompt_tokens_ollama", "prompt_tokens_ollama"),
        ("Completion tokens (Ollama)",     "completion_tokens_ollama", "completion_tokens_ollama"),
        ("Inference time (s)",             "inference_time_s", "inference_time_s"),
    ]
    for label, bkey, akey in metric_rows:
        bv = baseline.get(bkey, 0)
        cells = [label, str(bv)]
        for r in runs:
            av = r.get(akey, 0)
            dp = _delta_pct(float(bv), float(av))
            cells.append(f"{av} ({color(dp)})")
        t.add_row(*cells)

    console.print(t)

    for r in runs:
        name = labels.get(r.get("run", ""), r.get("run", ""))
        transforms = r.get("transforms_applied", [])
        console.print(
            f"\n[bold]{name}[/bold]  reduction: [bold]{_reduction_pct(r):.1f}%[/bold] "
            f"({r.get('tokens_saved', 0)} tokens removed)  "
            f"time: {_delta_pct(baseline['inference_time_s'], r['inference_time_s'])}")
        if transforms:
            console.print(f"  transforms: {', '.join(transforms)}")


def _plain_table(baseline: dict, runs: list[dict]):
    labels = {"with_headroom": "Rule-based", "with_kompress": "+Kompress"}
    print("\n=== COMPRESSION COMPARISON ===")
    header = f"  {'Metric':<34} {'Baseline':>10}"
    for r in runs:
        header += f" {labels.get(r.get('run',''), r.get('run','')):>16}"
    print(header)
    print("  " + "-" * (46 + 17 * len(runs)))

    metric_rows = [
        ("Send token estimate", "raw_token_estimate", "send_token_estimate"),
        ("Prompt tokens (Ollama)", "prompt_tokens_ollama", "prompt_tokens_ollama"),
        ("Completion tokens (Ollama)", "completion_tokens_ollama", "completion_tokens_ollama"),
        ("Inference time (s)", "inference_time_s", "inference_time_s"),
    ]
    for label, bkey, akey in metric_rows:
        bv = baseline.get(bkey, 0)
        line = f"  {label:<34} {str(bv):>10}"
        for r in runs:
            av = r.get(akey, 0)
            line += f" {f'{av} ({_delta_pct(float(bv), float(av))})':>16}"
        print(line)

    for r in runs:
        name = labels.get(r.get("run", ""), r.get("run", ""))
        print(f"\n  {name:<12} reduction: {_reduction_pct(r):.1f}%  "
              f"({r.get('tokens_saved', 0)} tokens removed)  "
              f"time: {_delta_pct(baseline['inference_time_s'], r['inference_time_s'])}")
        transforms = r.get("transforms_applied", [])
        if transforms:
            print(f"  {'':<12} transforms: {', '.join(transforms)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--no-kompress", action="store_true",
                        help="skip the Kompress ML run (rule-based only)")
    args = parser.parse_args()

    print("\n── Baseline run ──────────────────────────────")
    before = _run_config("baseline")

    if args.baseline_only:
        return

    print("\n── Rule-based run ────────────────────────────")
    rule_based = _run_config("with_headroom")

    runs = [rule_based]
    out = {"baseline": before, "with_headroom": rule_based}

    if not args.no_kompress:
        print("\n── Kompress (ML) run ─────────────────────────")
        kompress = _run_config("with_kompress")
        runs.append(kompress)
        out["with_kompress"] = kompress

    print("\n")
    print_table(before, runs)

    if args.save:
        Path("results.json").write_text(json.dumps(out, indent=2))
        print("\nSaved → results.json")


if __name__ == "__main__":
    main()
