"""
Eval runner: run an agent against all tasks and record structured results.

The deliverable is not "an agent that works" — it's a table of (model, rung, task, pass/fail)
so you can plot rung vs pass-rate and measure what the harness is actually worth.
"""
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from langchain_core.messages import HumanMessage

TASKS_DIR = Path(__file__).parent.parent / "tasks"


@dataclass
class RunResult:
    model: str
    rung: int
    task_id: str
    passed: bool
    latency_ms: float
    n_messages: int
    verify_attempts: int
    error: str | None = None


def get_model(name: str):
    """Resolve a model name string to a LangChain chat model instance."""
    if name == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-sonnet-4-6")
    if name.startswith("ollama:"):
        from langchain_ollama import ChatOllama
        return ChatOllama(model=name.split(":", 1)[1])
    raise ValueError(f"Unknown model '{name}'. Use 'claude' or 'ollama:<model>'.")


def reset_task(task_dir: Path) -> None:
    """
    Reset solution.py to its original stub before each agent run.
    Backs up the stub on the first call so subsequent resets work correctly.
    Also removes any plan/scratch files left from the previous run.
    """
    solution = task_dir / "solution.py"
    stub = task_dir / ".solution_stub.py"

    if not stub.exists() and solution.exists():
        stub.write_text(solution.read_text())

    if stub.exists():
        solution.write_text(stub.read_text())

    for fname in [".plan.json", ".scratch.json"]:
        p = task_dir / fname
        if p.exists():
            p.unlink()


def _verify_solution(task_dir: Path) -> bool:
    """Run pytest and return True if all tests pass."""
    result = subprocess.run(
        ["python", "-m", "pytest", str(task_dir / "test_solution.py"), "-q", "--no-header", "--tb=no"],
        capture_output=True,
        text=True,
        cwd=str(task_dir),
        timeout=30,
    )
    return result.returncode == 0


def run_once(model_name: str, rung: int, task_dir: Path) -> RunResult:
    """Run one agent on one task and return a structured result."""
    from harness.builder import build_agent

    task_id = task_dir.name
    reset_task(task_dir)

    model = get_model(model_name)
    agent = build_agent(model, rung, task_dir)
    description = (task_dir / "description.md").read_text()

    initial_state = {
        "messages": [HumanMessage(content=description)],
        "task_id": task_id,
        "rung": rung,
        "verify_attempts": 0,
        "passed": None,
    }

    start = time.time()
    try:
        final = agent.invoke(initial_state, {"recursion_limit": 60})
        latency = (time.time() - start) * 1000

        # Rung 3+ sets passed in state; lower rungs need a final manual check.
        passed = final.get("passed")
        if passed is None:
            passed = _verify_solution(task_dir)

        return RunResult(
            model=model_name,
            rung=rung,
            task_id=task_id,
            passed=bool(passed),
            latency_ms=latency,
            n_messages=len(final["messages"]),
            verify_attempts=final.get("verify_attempts", 0),
        )
    except Exception as exc:
        return RunResult(
            model=model_name,
            rung=rung,
            task_id=task_id,
            passed=False,
            latency_ms=(time.time() - start) * 1000,
            n_messages=0,
            verify_attempts=0,
            error=str(exc),
        )


def run_sweep(models: list[str], rungs: list[int], verbose: bool = True) -> list[RunResult]:
    """
    Full sweep: for every (model, rung, task) triple, run the agent and collect results.

    Run A pattern: run_sweep(models=["claude", "ollama:qwen3:8b"], rungs=[5])
    Run B pattern: run_sweep(models=["ollama:qwen3:8b"], rungs=[0, 1, 2, 3, 4, 5])
    """
    tasks = sorted(p for p in TASKS_DIR.iterdir() if p.is_dir() and p.name.startswith("task_"))
    results: list[RunResult] = []

    for model_name in models:
        for rung in rungs:
            for task_dir in tasks:
                label = f"[{model_name}] rung={rung} {task_dir.name}"
                if verbose:
                    print(f"  {label}... ", end="", flush=True)

                result = run_once(model_name, rung, task_dir)
                results.append(result)

                if verbose:
                    status = "PASS" if result.passed else f"FAIL ({result.error or 'tests'})"
                    print(status)

    return results
