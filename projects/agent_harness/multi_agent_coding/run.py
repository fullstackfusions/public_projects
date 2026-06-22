#!/usr/bin/env python3
"""
Autonomous Multi-Agent Coding System — entry point.

4 agents work in sequence: PLANNER → CODER → EVALUATOR → DEBUGGER (loop)
All inference runs locally via Ollama — no cloud API required.
A proof document is generated after each run.

Usage:
  python run.py --demo 1                        # email validator (recommended first run)
  python run.py --demo 2                        # url slug generator
  python run.py --demo 3                        # run-length encoding
  python run.py --list-demos                    # show available demos

  # Your own task (you supply the test file):
  python run.py --task "implement X" --tests path/to/test.py

  # Use a different model:
  python run.py --demo 1 --model qwen3:8b
  python run.py --demo 1 --model claude-sonnet-4-6   # needs ANTHROPIC_API_KEY
"""
import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

load_dotenv()

ROOT = Path(__file__).parent
DEMOS_DIR = ROOT / "demos"
PROOFS_DIR = ROOT / "proofs"
WORKSPACE_BASE = ROOT / "workspace"
CONSOLE = Console()

AGENT_EMOJI = {
    "planner": "🗺️ ",
    "coder": "💻",
    "evaluator": "🧪",
    "debugger": "🔧",
}
AGENT_COLOR = {
    "planner": "cyan",
    "coder": "green",
    "evaluator": "yellow",
    "debugger": "magenta",
}


def get_model(model_name: str):
    """Resolve a model name to a LangChain chat model."""
    ollama_prefixes = ("gemma", "llama", "qwen", "mistral", "deepseek", "phi", "codellama")
    if any(model_name.lower().startswith(p) for p in ollama_prefixes):
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model_name, temperature=0.1)
    if "claude" in model_name:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, temperature=0.1)
    # Default: try Ollama
    from langchain_ollama import ChatOllama
    return ChatOllama(model=model_name, temperature=0.1)


def run_with_stream(task: str, tests_path: str, model_name: str, workspace_dir: Path) -> dict:
    """Run the pipeline with real-time progress output using LangGraph streaming."""
    from system import build_pipeline, CodingState, MAX_ITERATIONS
    from langchain_core.messages import HumanMessage

    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "solution.py").write_text("# placeholder\n")

    model = get_model(model_name)
    pipeline = build_pipeline(model)

    import time as _time
    initial: CodingState = {
        "task": task,
        "workspace": str(workspace_dir),
        "tests_path": str(Path(tests_path).resolve()),
        "plan": "",
        "code": "",
        "test_output": "",
        "passed": None,
        "iteration": 0,
        "t_start": _time.time(),
        "logs": [],
    }

    # stream_mode="updates" gives {node_name: delta} per step — use for progress display.
    # We track the full accumulated state ourselves so logs are correct.
    import _operator as op
    accumulated = dict(initial)
    accumulated["logs"] = []

    for event in pipeline.stream(initial, {"recursion_limit": 30}, stream_mode="updates"):
        for node_name, updates in event.items():
            if node_name.startswith("__"):
                continue

            # Merge update into accumulated state (logs use add-reducer)
            for k, v in updates.items():
                if k == "logs":
                    accumulated["logs"] = accumulated.get("logs", []) + v
                else:
                    accumulated[k] = v

            color = AGENT_COLOR.get(node_name, "white")
            emoji = AGENT_EMOJI.get(node_name, "🤖")
            new_logs = updates.get("logs", [])
            last_log = new_logs[-1] if new_logs else None
            duration = f"{last_log['t_end'] - last_log['t_start']:.1f}s" if last_log else ""

            if node_name == "evaluator":
                passed = updates.get("passed")
                status = "[green]✅ PASSED[/green]" if passed else "[red]❌ FAILED[/red]"
                CONSOLE.print(f"  {emoji} [{color}][{node_name.upper()}][/{color}]  {status}  ({duration})")
            elif node_name == "coder":
                code = updates.get("code", "")
                lines = len(code.splitlines()) if code else 0
                CONSOLE.print(f"  {emoji} [{color}][{node_name.upper()}][/{color}]  Wrote {lines} lines  ({duration})")
            elif node_name == "debugger":
                iteration = updates.get("iteration", "?")
                CONSOLE.print(f"  {emoji} [{color}][{node_name.upper()}][/{color}]  Attempt {iteration}/{MAX_ITERATIONS}  ({duration})")
            else:
                CONSOLE.print(f"  {emoji} [{color}][{node_name.upper()}][/{color}]  Done  ({duration})")

    return accumulated


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Multi-Agent Coding System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--demo", type=int, choices=[1, 2, 3], help="Run demo task 1–3")
    parser.add_argument("--task", help="Task description (natural language)")
    parser.add_argument("--tests", help="Path to pytest test file (required with --task)")
    parser.add_argument("--model", default="gemma3:12b", help="Model name (default: gemma3:12b)")
    parser.add_argument("--list-demos", action="store_true", help="List available demos")
    args = parser.parse_args()

    if args.list_demos:
        CONSOLE.print("\n[bold]Available demos:[/bold]")
        for d in sorted(DEMOS_DIR.iterdir()):
            if d.is_dir():
                task_file = d / "task.md"
                if task_file.exists():
                    title = task_file.read_text().splitlines()[0].lstrip("# ")
                    CONSOLE.print(f"  [cyan]{d.name}[/cyan]  {title}")
        return

    if args.demo:
        demo_dir = DEMOS_DIR / f"task_0{args.demo}"
        if not demo_dir.exists():
            CONSOLE.print(f"[red]Demo {args.demo} not found[/red]")
            sys.exit(1)
        task = (demo_dir / "task.md").read_text().strip()
        tests_path = str(demo_dir / "test.py")
        workspace_dir = WORKSPACE_BASE / f"run_{args.demo}"
    elif args.task and args.tests:
        task = args.task
        tests_path = args.tests
        workspace_dir = WORKSPACE_BASE / f"run_custom_{int(time.time())}"
    else:
        parser.print_help()
        return

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    CONSOLE.print()
    CONSOLE.print(Panel.fit(
        f"[bold]Autonomous Multi-Agent Coding System[/bold]\n"
        f"Model: [cyan]{args.model}[/cyan]  |  Local inference via Ollama\n"
        f"Task:  {task[:80]}{'...' if len(task) > 80 else ''}",
        border_style="blue",
    ))
    CONSOLE.print()

    # -----------------------------------------------------------------------
    # Run
    # -----------------------------------------------------------------------
    t_wall = time.time()
    final = run_with_stream(task, tests_path, args.model, workspace_dir)
    elapsed = time.time() - t_wall

    # -----------------------------------------------------------------------
    # Generate proof
    # -----------------------------------------------------------------------
    from proof import generate_proof

    # final already has the fully accumulated state from run_with_stream
    final["t_start"] = t_wall  # restore wall-clock reference
    proof_path = generate_proof(final, args.model, PROOFS_DIR)

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    CONSOLE.print()
    CONSOLE.print(Rule())
    passed = final.get("passed")
    result_str = "[green]✅ PASSED[/green]" if passed else "[red]❌ FAILED[/red]"
    CONSOLE.print(f"  Result   : {result_str}")
    CONSOLE.print(f"  Duration : {elapsed:.1f}s")
    CONSOLE.print(f"  Proof    : [bold]{proof_path}[/bold]")
    CONSOLE.print(f"  Solution : [bold]{workspace_dir}/solution.py[/bold]")
    CONSOLE.print(Rule())
    CONSOLE.print()

    if proof_path.exists():
        CONSOLE.print(f"[dim]View proof: open {proof_path}[/dim]")
        CONSOLE.print(f"[dim]View code:  cat {workspace_dir}/solution.py[/dim]")
    CONSOLE.print()


if __name__ == "__main__":
    main()
