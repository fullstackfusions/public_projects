"""
Report eval results: rich table, summary pass-rate table, JSON export, optional chart.

The chart is the deliverable: rung on x-axis, pass-rate on y-axis, one line per model.
The shape of that curve IS the finding.
"""
import json
from collections import defaultdict
from dataclasses import asdict

from eval.runner import RunResult


def print_table(results: list[RunResult]) -> None:
    """Print every individual run as a rich table."""
    from rich.table import Table
    from rich.console import Console

    table = Table(title="Harness Ladder — Individual Run Results")
    table.add_column("Model", style="cyan", no_wrap=True)
    table.add_column("Rung", style="yellow", justify="right")
    table.add_column("Task", style="white")
    table.add_column("Pass", justify="center")
    table.add_column("Latency (ms)", justify="right")
    table.add_column("Verify Attempts", justify="right")
    table.add_column("Error", style="red")

    for r in results:
        table.add_row(
            r.model,
            str(r.rung),
            r.task_id,
            "[green]✓[/green]" if r.passed else "[red]✗[/red]",
            f"{r.latency_ms:.0f}",
            str(r.verify_attempts),
            r.error or "",
        )

    Console().print(table)


def summary_table(results: list[RunResult]) -> None:
    """Print aggregated pass-rate by (model, rung)."""
    from rich.table import Table
    from rich.console import Console

    totals: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
    for r in results:
        key = (r.model, r.rung)
        totals[key][1] += 1
        if r.passed:
            totals[key][0] += 1

    table = Table(title="Pass Rate by Model × Rung  (this is the chart data)")
    table.add_column("Model", style="cyan")
    table.add_column("Rung", style="yellow", justify="right")
    table.add_column("Pass Rate", justify="right")
    table.add_column("Passed / Total", justify="right")

    for (model, rung), (passed, total) in sorted(totals.items()):
        pct = f"{100 * passed / total:.0f}%" if total else "—"
        table.add_row(model, str(rung), pct, f"{passed}/{total}")

    Console().print(table)


def save_results(results: list[RunResult], path: str = "results.json") -> None:
    with open(path, "w") as fh:
        json.dump([asdict(r) for r in results], fh, indent=2)
    print(f"Results saved → {path}")


def plot_ladder(results: list[RunResult], output: str = "ladder_chart.png") -> None:
    """
    Plot rung vs pass-rate, one line per model.

    Install extras first: pip install pandas matplotlib
    """
    try:
        import matplotlib.pyplot as plt
        import pandas as pd
    except ImportError:
        print("Skip chart — install extras: pip install pandas matplotlib")
        return

    df = pd.DataFrame([asdict(r) for r in results])
    agg = df.groupby(["model", "rung"])["passed"].mean().reset_index()
    agg["pass_pct"] = agg["passed"] * 100

    fig, ax = plt.subplots(figsize=(10, 6))
    for model in sorted(agg["model"].unique()):
        sub = agg[agg["model"] == model].sort_values("rung")
        ax.plot(sub["rung"], sub["pass_pct"], marker="o", linewidth=2, label=model)

    ax.set_xlabel("Harness Rung", fontsize=13)
    ax.set_ylabel("Pass Rate (%)", fontsize=13)
    ax.set_title("The Harness Ladder: how much of reliability comes from the harness?", fontsize=14)
    ax.set_xticks(sorted(agg["rung"].unique()))
    ax.set_xticklabels([
        f"Rung {r}\n{_rung_label(r)}" for r in sorted(agg["rung"].unique())
    ], fontsize=9)
    ax.set_ylim(0, 105)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    print(f"Chart saved → {output}")


def _rung_label(rung: int) -> str:
    labels = {
        0: "bare",
        1: "+plan",
        2: "+memory",
        3: "+verify",
        4: "+sandbox",
        5: "+sub-agents",
    }
    return labels.get(rung, "")
