"""
Tool factory: get_tools(rung, task_dir, model=None) → list[BaseTool]

Each rung stacks capabilities on the previous:
  0: read_file, write_file, list_files, run_tests
  1: + create_plan, mark_step_done, get_plan
  2: + scratch_write, scratch_read
  3: no new tools — self-verify is a LangGraph node, not a tool
        (This is the lesson: the harness enforces the feedback loop; the model doesn't opt in.)
  4: write_file is replaced by sandboxed_write_file (solution.py only)
  5: + delegate_subtask (isolated sub-agent call)
"""
import json
import subprocess
from pathlib import Path

from langchain_core.tools import tool as make_tool


def get_tools(rung: int, task_dir: Path, model=None) -> list:
    task_dir = Path(task_dir)

    tools = _file_tools(task_dir, sandboxed=(rung >= 4))
    tools.append(_test_tool(task_dir))

    if rung >= 1:
        tools.extend(_plan_tools(task_dir))

    if rung >= 2:
        tools.extend(_scratch_tools(task_dir))

    if rung >= 5 and model is not None:
        tools.append(_delegate_tool(task_dir, model))

    return tools


# ---------------------------------------------------------------------------
# Rung 0 — file I/O tools
# ---------------------------------------------------------------------------

def _file_tools(task_dir: Path, sandboxed: bool = False) -> list:
    @make_tool
    def read_file(path: str) -> str:
        """Read a file from the task directory. path is relative to the task dir."""
        full = task_dir / path
        if not full.exists():
            available = [f.name for f in task_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
            return f"ERROR: '{path}' not found. Available files: {available}"
        return full.read_text()

    @make_tool
    def list_files() -> str:
        """List all files in the task directory."""
        files = sorted(f.name for f in task_dir.iterdir() if f.is_file() and not f.name.startswith("."))
        return "\n".join(files) if files else "(empty)"

    if sandboxed:
        @make_tool
        def write_file(path: str, content: str) -> str:
            """[SANDBOXED] Write to solution.py ONLY. Writes to any other path are rejected."""
            if path != "solution.py":
                return f"SANDBOX REJECTED: can only write to solution.py, got '{path}'"
            (task_dir / "solution.py").write_text(content)
            return f"Written {len(content)} chars to solution.py"
    else:
        @make_tool
        def write_file(path: str, content: str) -> str:
            """Write content to a file in the task directory. Only write to solution.py."""
            if path.startswith("..") or path.startswith("/"):
                return "ERROR: path traversal not allowed"
            (task_dir / path).write_text(content)
            return f"Written {len(content)} chars to {path}"

    return [read_file, write_file, list_files]


# ---------------------------------------------------------------------------
# Rung 0 — test runner (used directly by agent AND by verify node in rung 3)
# ---------------------------------------------------------------------------

def _test_tool(task_dir: Path):
    @make_tool
    def run_tests() -> str:
        """Run the pytest test suite for this task. Returns full output with pass/fail details."""
        test_file = task_dir / "test_solution.py"
        if not test_file.exists():
            return "No test_solution.py found in task directory."
        result = subprocess.run(
            ["python", "-m", "pytest", str(test_file), "-v", "--tb=short", "--no-header"],
            capture_output=True,
            text=True,
            cwd=str(task_dir),
            timeout=30,
        )
        return result.stdout + result.stderr

    return run_tests


# ---------------------------------------------------------------------------
# Rung 1 — planning tools
# Lesson: structure alone (decompose → track) often produces the biggest single jump.
# ---------------------------------------------------------------------------

def _plan_tools(task_dir: Path) -> list:
    plan_file = task_dir / ".plan.json"

    @make_tool
    def create_plan(steps: list[str]) -> str:
        """
        Create a step-by-step plan BEFORE writing any code.
        steps: ordered list of strings describing each action.
        """
        plan = {"steps": steps, "done": [False] * len(steps)}
        plan_file.write_text(json.dumps(plan, indent=2))
        lines = [f"  [{i}] {s}" for i, s in enumerate(steps)]
        return f"Plan created ({len(steps)} steps):\n" + "\n".join(lines)

    @make_tool
    def mark_step_done(step_index: int) -> str:
        """Mark a plan step as completed. step_index is 0-based."""
        if not plan_file.exists():
            return "No plan found. Call create_plan first."
        plan = json.loads(plan_file.read_text())
        if step_index >= len(plan["steps"]):
            return f"Invalid index {step_index}. Plan has {len(plan['steps'])} steps."
        plan["done"][step_index] = True
        plan_file.write_text(json.dumps(plan, indent=2))
        remaining = [s for s, d in zip(plan["steps"], plan["done"]) if not d]
        return f"Step {step_index} done. Remaining: {remaining}"

    @make_tool
    def get_plan() -> str:
        """Get the current plan and its completion status."""
        if not plan_file.exists():
            return "No plan yet. Call create_plan first."
        plan = json.loads(plan_file.read_text())
        lines = []
        for i, (step, done) in enumerate(zip(plan["steps"], plan["done"])):
            lines.append(f"  [{'✓' if done else ' '}] {i}: {step}")
        return "\n".join(lines)

    return [create_plan, mark_step_done, get_plan]


# ---------------------------------------------------------------------------
# Rung 2 — scratch memory
# Lesson: many failures are context failures, not capability failures.
#         A named scratchpad lets the model offload working memory to disk.
# ---------------------------------------------------------------------------

def _scratch_tools(task_dir: Path) -> list:
    scratch_file = task_dir / ".scratch.json"

    @make_tool
    def scratch_write(key: str, value: str) -> str:
        """Save a note to persistent scratch memory. Use short keys like 'edge_cases', 'algorithm'."""
        scratch = json.loads(scratch_file.read_text()) if scratch_file.exists() else {}
        scratch[key] = value
        scratch_file.write_text(json.dumps(scratch, indent=2))
        return f"Saved '{key}' to scratch."

    @make_tool
    def scratch_read(key: str = "") -> str:
        """Read from scratch memory. Pass a key for one note, or '' to dump all notes."""
        if not scratch_file.exists():
            return "Scratch is empty."
        scratch = json.loads(scratch_file.read_text())
        if not scratch:
            return "Scratch is empty."
        if key:
            return scratch.get(key, f"No note with key '{key}'. Keys: {list(scratch)}")
        return json.dumps(scratch, indent=2)

    return [scratch_write, scratch_read]


# ---------------------------------------------------------------------------
# Rung 5 — sub-agent delegation
# Lesson: isolated context per subtask beats one long accumulating context.
#         The sub-agent here is a rung-0 agent with a clean context window.
# ---------------------------------------------------------------------------

def _delegate_tool(task_dir: Path, model):
    @make_tool
    def delegate_subtask(description: str) -> str:
        """
        Delegate a focused sub-problem to a specialist sub-agent.
        The sub-agent gets a clean context and returns its analysis/answer as text.
        Use this to research an algorithm, analyze edge cases, or draft a sub-component
        before you write the final solution.py yourself.
        """
        from langchain_core.messages import SystemMessage, HumanMessage

        sub_system = (
            "You are a specialist coding assistant. "
            "Answer the question concisely and precisely. "
            "Return only the information requested — no preamble."
        )
        response = model.invoke([
            SystemMessage(content=sub_system),
            HumanMessage(content=description),
        ])
        return response.content

    return delegate_subtask
