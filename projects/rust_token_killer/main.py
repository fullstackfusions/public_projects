"""
RTK Token Killer — LangGraph Demo
Usage:
  python main.py benchmark          # measure token savings per command (no LLM)
  python main.py agent [task]       # run LangGraph agent in raw vs RTK mode
  python main.py demo               # benchmark + agent back to back
"""

import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from rich import box

from config import BENCHMARK_COMMANDS, DEMO_TASK
from benchmark import run_benchmark
from agent import run_agent
from shell_tools import rtk_available
from utils import savings_pct

console = Console()

_HEADER = (
    "[bold cyan]RTK Token Killer[/bold cyan]  "
    "[dim]LangGraph · Qwen2.5:7b (Ollama)[/dim]"
)


def _print_banner(subtitle: str):
    console.print(Panel(f"{_HEADER}\n[dim]{subtitle}[/dim]", border_style="cyan", expand=False))


# ── benchmark ──────────────────────────────────────────────────────────────────


def cmd_benchmark():
    _print_banner("Mode: benchmark — measure tool-output token savings without running an LLM")

    rtk_ok = rtk_available()
    if not rtk_ok:
        console.print("\n[yellow]⚠  RTK not installed — showing raw token counts only.[/yellow]")
        console.print("[dim]   Install with: bash setup.sh[/dim]\n")

    results = []
    for cmd in track(BENCHMARK_COMMANDS, description="[cyan]Running commands...[/cyan]"):
        results.append(run_benchmark([cmd])[0])

    table = Table(
        title="\n[bold]Shell Output — Token Comparison[/bold]",
        box=box.ROUNDED,
        border_style="cyan",
        show_footer=True,
        footer_style="bold",
        min_width=72,
    )

    total_raw = sum(r["raw_tokens"] for r in results)

    table.add_column("Command", style="white", footer="TOTAL")
    table.add_column("Raw Tokens", justify="right", style="red", footer=f"{total_raw:,}")

    if rtk_ok:
        total_rtk = sum(r["rtk_tokens"] for r in results)
        overall = savings_pct(total_raw, total_rtk)

        table.add_column("RTK Tokens", justify="right", style="green", footer=f"{total_rtk:,}")
        table.add_column("Savings", justify="right", style="bold yellow", footer=f"{overall:.1f}%")

        for r in results:
            table.add_row(
                r["command"],
                f"{r['raw_tokens']:,}",
                f"{r['rtk_tokens']:,}",
                f"{r['savings_pct']:.1f}%",
            )

        console.print(table)
        console.print(
            f"\n[bold green]✓ RTK eliminated {total_raw - total_rtk:,} tokens "
            f"({overall:.1f}% savings) across {len(results)} commands.[/bold green]\n"
        )
    else:
        for r in results:
            table.add_row(r["command"], f"{r['raw_tokens']:,}")
        console.print(table)


# ── agent ──────────────────────────────────────────────────────────────────────


def cmd_agent(task: str | None = None):
    _print_banner("Mode: agent — LangGraph ReAct agent with raw vs RTK bash tools")

    rtk_ok = rtk_available()
    task = task or DEMO_TASK

    console.print(f"\n[bold]Task:[/bold] {task}\n")

    if not rtk_ok:
        console.print("[yellow]⚠  RTK not installed — running raw mode only.[/yellow]\n")

    modes = ["raw", "rtk"] if rtk_ok else ["raw"]
    results: dict[str, dict] = {}

    for mode in modes:
        label = "[cyan]RAW[/cyan]" if mode == "raw" else "[green]RTK[/green]"
        console.print(f"[bold]▶ Running agent — {label} mode[/bold]")
        results[mode] = run_agent(task, mode=mode)
        rec = results[mode]
        console.print(
            f"[dim]  {rec['tool_calls']} tool call(s) · "
            f"{rec['total_tool_tokens']:,} tool-output tokens consumed[/dim]\n"
        )

    display = "rtk" if rtk_ok else "raw"
    console.print(Panel(
        results[display]["response"],
        title="[bold green]Agent Response[/bold green]",
        border_style="green",
    ))

    if rtk_ok:
        raw_t = results["raw"]["total_tool_tokens"]
        rtk_t = results["rtk"]["total_tool_tokens"]
        pct = savings_pct(raw_t, rtk_t)

        console.print("\n[bold]Context Window Impact — Tool Outputs:[/bold]")
        console.print(f"  [red]Raw mode :[/red]  {raw_t:,} tokens fed back into LLM context")
        console.print(f"  [green]RTK mode :[/green]  {rtk_t:,} tokens fed back into LLM context")
        console.print(
            f"  [bold yellow]Savings  :[/bold yellow]  {pct:.1f}%  "
            f"({raw_t - rtk_t:,} tokens) — RTK compressed the context\n"
        )

        _print_per_call_table(results)


def _print_per_call_table(results: dict):
    raw_records = results["raw"]["records"]
    rtk_records = results["rtk"]["records"]

    if not raw_records:
        return

    table = Table(
        title="[bold]Per-Call Breakdown[/bold]",
        box=box.SIMPLE_HEAVY,
        border_style="dim",
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("Command", style="white")
    table.add_column("Raw Tokens", justify="right", style="red")
    table.add_column("RTK Tokens", justify="right", style="green")
    table.add_column("Savings", justify="right", style="yellow")

    for i, (r, k) in enumerate(zip(raw_records, rtk_records), 1):
        pct = savings_pct(r.tokens, k.tokens)
        table.add_row(str(i), r.command, f"{r.tokens:,}", f"{k.tokens:,}", f"{pct:.1f}%")

    console.print(table)


# ── demo ───────────────────────────────────────────────────────────────────────


def cmd_demo():
    cmd_benchmark()
    console.print("─" * 72)
    cmd_agent()


# ── entry point ────────────────────────────────────────────────────────────────


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "benchmark"

    if cmd == "benchmark":
        cmd_benchmark()
    elif cmd == "agent":
        task = " ".join(args[1:]) if len(args) > 1 else None
        cmd_agent(task)
    elif cmd == "demo":
        cmd_demo()
    else:
        console.print(f"[red]Unknown command: {cmd}[/red]")
        console.print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
