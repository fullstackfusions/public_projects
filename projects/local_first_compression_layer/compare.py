"""
Runs both graphs back-to-back and prints a comparison table.

Usage:
  python compare.py           # run both, print table
  python compare.py --save    # also write results.json
  python compare.py --baseline-only
"""

import argparse
import json
from pathlib import Path

from projects.local_first_compression_layer.baseline import main as run_baseline
from projects.local_first_compression_layer.with_headroom import main as run_headroom


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


def print_table(b: dict, a: dict):
    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box
        _rich_table(Console(), b, a, box)
    except ImportError:
        _plain_table(b, a)


def _rich_table(console, b: dict, a: dict, box):
    from rich.table import Table

    def color(val: str) -> str:
        if val.startswith("-"):
            return f"[green]{val}[/green]"
        if val.startswith("+") and val != "+0":
            return f"[red]{val}[/red]"
        return val

    t = Table(title=f"Headroom vs Baseline  |  model: {b['model']}", box=box.ROUNDED, show_lines=True)
    t.add_column("Metric", style="cyan", min_width=30)
    t.add_column("Baseline", justify="right")
    t.add_column("With Headroom", justify="right")
    t.add_column("Delta", justify="right")

    rows = [
        ("Token estimate (pre-send, tiktoken)",
            "raw_token_estimate", "send_token_estimate", _delta_pct),
        ("Prompt tokens (Ollama reported)",
            "prompt_tokens_ollama", "prompt_tokens_ollama", _delta_pct),
        ("Completion tokens (Ollama reported)",
            "completion_tokens_ollama", "completion_tokens_ollama", _delta_pct),
        ("Inference time (s)",
            "inference_time_s", "inference_time_s", _delta_pct),
    ]

    for label, bkey, akey in [
        ("Token estimate (pre-send, tiktoken)", "raw_token_estimate", "send_token_estimate"),
        ("Prompt tokens (Ollama reported)",     "prompt_tokens_ollama", "prompt_tokens_ollama"),
        ("Completion tokens (Ollama reported)", "completion_tokens_ollama", "completion_tokens_ollama"),
        ("Inference time (s)",                  "inference_time_s", "inference_time_s"),
    ]:
        bv = b.get(bkey, 0)
        av = a.get(akey, 0)
        dp = _delta_pct(float(bv), float(av))
        t.add_row(label, str(bv), str(av), color(dp))

    console.print(t)

    tokens_saved = a.get("tokens_saved", b["raw_token_estimate"] - a["send_token_estimate"])
    ratio = a.get("compression_ratio", 1.0)
    compression_pct = round((1 - ratio) * 100, 1)
    transforms = a.get("transforms_applied", [])
    console.print(f"\nContext reduction: [bold]{compression_pct:.1f}%[/bold]  "
                  f"({tokens_saved} tokens removed before send)")
    if transforms:
        console.print(f"Transforms applied: {', '.join(transforms)}")
    console.print(f"Time delta: {_delta_pct(b['inference_time_s'], a['inference_time_s'])}")


def _plain_table(b: dict, a: dict):
    print("\n=== COMPRESSION COMPARISON ===")
    print(f"  {'Metric':<40} {'Baseline':>10} {'Headroom':>12} {'Delta':>10}")
    print("  " + "-" * 74)

    rows = [
        ("Token estimate (pre-send)",    b["raw_token_estimate"],    a["send_token_estimate"]),
        ("Prompt tokens (Ollama)",        b["prompt_tokens_ollama"], a["prompt_tokens_ollama"]),
        ("Completion tokens (Ollama)",    b["completion_tokens_ollama"], a["completion_tokens_ollama"]),
        ("Inference time (s)",            b["inference_time_s"],     a["inference_time_s"]),
    ]
    for label, bv, av in rows:
        dp = _delta_pct(float(bv), float(av))
        print(f"  {label:<40} {str(bv):>10} {str(av):>12} {dp:>10}")

    tokens_saved = a.get("tokens_saved", b["raw_token_estimate"] - a["send_token_estimate"])
    ratio = a.get("compression_ratio", 1.0)
    compression_pct = round((1 - ratio) * 100, 1)
    print(f"\n  Context reduction : {compression_pct:.1f}%  ({tokens_saved} tokens removed)")
    transforms = a.get("transforms_applied", [])
    if transforms:
        print(f"  Transforms        : {', '.join(transforms)}")
    print(f"  Time delta        : {_delta_pct(b['inference_time_s'], a['inference_time_s'])}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--baseline-only", action="store_true")
    args = parser.parse_args()

    print("\n── Baseline run ──────────────────────────────")
    before = run_baseline()

    if args.baseline_only:
        return

    print("\n── Headroom run ──────────────────────────────")
    after = run_headroom()

    print("\n")
    print_table(before, after)

    if args.save:
        out = {"baseline": before, "with_headroom": after}
        Path("results.json").write_text(json.dumps(out, indent=2))
        print("\nSaved → results.json")


if __name__ == "__main__":
    main()
