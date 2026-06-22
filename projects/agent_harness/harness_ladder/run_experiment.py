#!/usr/bin/env python3
"""
Harness Ladder Experiment — entry point.

The experiment isolates the harness as the variable and measures what it's worth.

  Run A — vary the MODEL, hold rung constant at 5
           Measures: what the model contributes
           Signal:   gap between claude and ollama at rung=5

  Run B — vary the RUNG, hold model constant at the WEAK one (ollama)
           Measures: what the harness contributes  ← the main event
           Signal:   the curve shape as you climb the ladder

  full  — both A and B (all models × all rungs)

Single-task mode (--task, --rung, --model):
  Useful for interactive exploration — see the agent's full trace.

Usage:
  python run_experiment.py --mode B                              # main experiment
  python run_experiment.py --mode A                              # model comparison
  python run_experiment.py --mode full --no-plot                 # all, skip chart
  python run_experiment.py --task task_01 --rung 0 --model claude   # single run
  python run_experiment.py --task task_01 --rung 3 --model claude   # watch verify loop
  python run_experiment.py --list-tasks
"""

import argparse
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from eval.runner import TASKS_DIR, get_model, reset_task, run_once, run_sweep
from eval.reporter import plot_ladder, print_table, save_results, summary_table


def _single_run(model_name: str, rung: int, task_name: str) -> None:
    """Run one agent on one task with streaming-friendly output."""
    task_dir = TASKS_DIR / task_name
    if not task_dir.exists():
        print(f"Task not found: {task_name}")
        print(f"Available tasks: {[d.name for d in sorted(TASKS_DIR.iterdir()) if d.is_dir()]}")
        sys.exit(1)

    from harness.builder import build_agent
    from langchain_core.messages import HumanMessage

    print(f"\n{'='*60}")
    print(f"Model : {model_name}")
    print(f"Rung  : {rung}  ({_rung_description(rung)})")
    print(f"Task  : {task_name}")
    print(f"{'='*60}\n")

    reset_task(task_dir)
    model = get_model(model_name)
    agent = build_agent(model, rung, task_dir)
    description = (task_dir / "description.md").read_text()

    final = agent.invoke(
        {
            "messages": [HumanMessage(content=description)],
            "task_id": task_name,
            "rung": rung,
            "verify_attempts": 0,
            "passed": None,
        },
        {"recursion_limit": 60},
    )

    passed = final.get("passed")
    if passed is None:
        result = subprocess.run(
            ["python", "-m", "pytest", str(task_dir / "test_solution.py"), "-v", "--no-header"],
            cwd=str(task_dir),
        )
        passed = result.returncode == 0

    print(f"\n{'='*60}")
    print(f"Result : {'PASS ✓' if passed else 'FAIL ✗'}")
    print(f"Messages exchanged : {len(final['messages'])}")
    print(f"Verify attempts    : {final.get('verify_attempts', 0)}")
    print(f"{'='*60}\n")


def _rung_description(rung: int) -> str:
    desc = {
        0: "bare ReAct loop",
        1: "bare + planning",
        2: "bare + planning + memory",
        3: "bare + planning + memory + self-verify",
        4: "bare + planning + memory + self-verify + sandbox",
        5: "bare + planning + memory + self-verify + sandbox + sub-agents",
    }
    return desc.get(rung, f"rung {rung}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Harness Ladder Experiment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--mode", choices=["A", "B", "full"], help="Sweep mode")
    parser.add_argument("--task", help="Single task name, e.g. task_01")
    parser.add_argument("--rung", type=int, default=5, help="Harness rung 0-5 (default 5)")
    parser.add_argument("--model", default="claude", help="claude | ollama:<name> (default: claude)")
    parser.add_argument("--list-tasks", action="store_true", help="List available tasks and exit")
    parser.add_argument("--no-plot", action="store_true", help="Skip chart generation")
    parser.add_argument("--output", default="results.json", help="Results JSON path")
    args = parser.parse_args()

    if args.list_tasks:
        print("Available tasks:")
        for d in sorted(TASKS_DIR.iterdir()):
            if d.is_dir():
                desc_file = d / "description.md"
                title = desc_file.read_text().splitlines()[0].lstrip("# ") if desc_file.exists() else ""
                print(f"  {d.name}  —  {title}")
        return

    if args.task:
        _single_run(args.model, args.rung, args.task)
        return

    if not args.mode:
        parser.print_help()
        return

    # -------------------------------------------------------------------
    # Sweep mode
    # -------------------------------------------------------------------
    if args.mode == "A":
        print("\n=== Run A: Model comparison at rung=5 ===")
        print("Hypothesis: the frontier model outperforms the weak model.")
        print("Signal: gap between lines at rung=5 = model contribution.\n")
        results = run_sweep(models=["claude", "ollama:qwen3:8b"], rungs=[5])

    elif args.mode == "B":
        print("\n=== Run B: Harness ladder with weak model ===")
        print("Hypothesis: the harness closes most of the model gap.")
        print("Signal: the slope of the pass-rate curve as rung increases.\n")
        results = run_sweep(models=["ollama:qwen3:8b"], rungs=[0, 1, 2, 3, 4, 5])

    else:  # full
        print("\n=== Full experiment: all models × all rungs ===\n")
        results = run_sweep(
            models=["claude", "ollama:qwen3:8b"],
            rungs=[0, 1, 2, 3, 4, 5],
        )

    print()
    print_table(results)
    print()
    summary_table(results)
    print()
    save_results(results, args.output)

    if not args.no_plot:
        plot_ladder(results)

    # -------------------------------------------------------------------
    # Interpretation prompt
    # -------------------------------------------------------------------
    print("\n--- Interpretation guide ---")
    print("Big jump at rung 1 or 3  → model was capable but un-scaffolded; harness carries the task")
    print("Flat until late rung      → task needs capability the small model lacks; model floor binds")
    print("Weak model ≈ frontier     → the harness closed the model gap (this is the slide)")


if __name__ == "__main__":
    main()
