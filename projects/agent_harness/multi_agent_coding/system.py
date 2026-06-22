"""
Multi-Agent Coding System — core pipeline.

4 specialized agents, each a distinct LangGraph node:

  PLANNER    decomposes the task into steps + identifies edge cases
  CODER      writes the full implementation to solution.py
  EVALUATOR  runs pytest; passes result back as state (no LLM needed)
  DEBUGGER   analyzes failures, patches solution.py, increments iteration

The harness does all I/O (file writes, subprocess test runs).
The model only produces text. This separation is intentional:
"trust the LLM for reasoning, enforce boundaries at the harness level."

Graph:
  START → planner → coder → evaluator ─── pass ──→ END
                                  └── fail, iter < MAX ──→ debugger → evaluator
                                  └── fail, iter >= MAX ──→ END
"""
import ast
import operator
import re
import subprocess
import time
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

MAX_ITERATIONS = 3


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentLog(TypedDict):
    agent: str
    t_start: float
    t_end: float
    summary: str


class CodingState(TypedDict):
    task: str
    workspace: str       # directory where solution.py lives
    tests_path: str      # absolute path to the test file
    plan: str            # planner output
    code: str            # current solution code
    test_output: str     # latest pytest output
    passed: bool | None
    iteration: int       # number of debug cycles completed
    t_start: float       # wall clock when the run began
    logs: Annotated[list[AgentLog], operator.add]


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _extract_code(text: str) -> str:
    """
    Extract code from model output with multiple fallbacks.
    Models vary in whether they include the language tag.
    """
    # Preferred: ```python ... ```
    m = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Fallback: any ``` block
    m = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Last resort: return the whole text (model didn't use fences)
    return text.strip()


def _is_valid_python(code: str) -> tuple[bool, str]:
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, str(e)


def _run_tests(tests_path: str, workspace: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["python", "-m", "pytest", tests_path, "-v", "--tb=short", "--no-header"],
        capture_output=True,
        text=True,
        cwd=workspace,
        timeout=30,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def _log(agent: str, t0: float, t1: float, summary: str) -> AgentLog:
    return {"agent": agent, "t_start": t0, "t_end": t1, "summary": summary}


def _parse_failures(test_output: str) -> str:
    """
    Extract structured failure information from pytest output.
    Returns a concise, LLM-readable summary of what went wrong and what input caused it.
    """
    lines = test_output.splitlines()
    failures: list[str] = []
    in_block = False
    block: list[str] = []

    for line in lines:
        if line.startswith("FAILED ") or line.startswith("_ FAILED"):
            in_block = True
            block = [line]
        elif in_block:
            if line.startswith("=") or line.startswith("_"):
                if block:
                    failures.append("\n".join(block))
                block = []
                in_block = False
            else:
                block.append(line)

    if block:
        failures.append("\n".join(block))

    # Also pull out the short-form "assert" lines and "where" lines
    assert_lines = [
        l.strip() for l in lines
        if l.strip().startswith(("assert ", "AssertionError", "+  where", "E "))
    ]

    summary = ""
    if assert_lines:
        summary = "Specific assertion failures (read these carefully):\n"
        summary += "\n".join(assert_lines[:30])

    # Pull out FAILED test names
    failed_tests = [l for l in lines if l.startswith("FAILED")]
    if failed_tests:
        summary += "\n\nFailed tests:\n" + "\n".join(failed_tests)

    return summary or test_output[-800:]


# ---------------------------------------------------------------------------
# Agent node factories
# ---------------------------------------------------------------------------

def make_planner(model: BaseChatModel):
    def planner(state: CodingState) -> dict:
        t0 = time.time()
        resp = model.invoke([
            SystemMessage(content=(
                "You are a senior software architect. Given a coding task, produce a clear plan.\n\n"
                "Format your response as:\n"
                "## Steps\n1. ...\n2. ...\n\n"
                "## Edge Cases\n- ...\n- ...\n\n"
                "## Approach\nOne paragraph on the recommended algorithm/data structure.\n\n"
                "Be concise. No code yet — plan only."
            )),
            HumanMessage(content=f"Plan the implementation for:\n\n{state['task']}"),
        ])
        plan = resp.content.strip()
        t1 = time.time()
        return {
            "plan": plan,
            "logs": [_log("PLANNER", t0, t1, plan)],
        }
    return planner


def make_coder(model: BaseChatModel):
    def coder(state: CodingState) -> dict:
        t0 = time.time()
        resp = model.invoke([
            SystemMessage(content=(
                "You are an expert Python developer. Write a complete, working implementation.\n\n"
                "STRICT RULES:\n"
                "1. Output ONE ```python code block — nothing else outside it\n"
                "2. Include ALL necessary imports at the top\n"
                "3. Implement EVERY requirement from the task\n"
                "4. Handle ALL edge cases mentioned in the plan\n"
                "5. The code must be runnable as-is — no placeholders, no TODO comments"
            )),
            HumanMessage(content=(
                f"TASK:\n{state['task']}\n\n"
                f"PLAN:\n{state['plan']}\n\n"
                "Write the complete implementation now:"
            )),
        ])

        code = _extract_code(resp.content)
        valid, err = _is_valid_python(code)

        workspace = Path(state["workspace"])
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "solution.py").write_text(code)

        note = f"syntax error: {err}" if not valid else f"{len(code.splitlines())} lines written"
        t1 = time.time()
        return {
            "code": code,
            "logs": [_log("CODER", t0, t1, f"Wrote solution.py ({note})")],
        }
    return coder


def make_evaluator():
    def evaluator(state: CodingState) -> dict:
        t0 = time.time()
        passed, output = _run_tests(state["tests_path"], state["workspace"])
        t1 = time.time()

        if passed:
            summary = f"✅ All tests PASSED\n\n{output}"
        else:
            # Surface just the failure lines for readability in the proof
            failure_lines = [l for l in output.splitlines() if "FAILED" in l or "ERROR" in l or "assert" in l.lower()]
            summary = "❌ Tests FAILED\n\n" + "\n".join(failure_lines[:20]) + "\n\n" + output[-600:]

        return {
            "test_output": output,
            "passed": passed,
            "logs": [_log("EVALUATOR", t0, t1, summary)],
        }
    return evaluator


def make_debugger(model: BaseChatModel):
    def debugger(state: CodingState) -> dict:
        t0 = time.time()
        iteration = state["iteration"] + 1
        failure_summary = _parse_failures(state["test_output"])

        resp = model.invoke([
            SystemMessage(content=(
                "You are an expert Python debugger. Your job is to fix failing tests.\n\n"
                "PROCESS (follow in order):\n"
                "1. Read each failing test name and its assertion error\n"
                "2. For EACH failure, answer: what input caused it? what did the function return? what should it return?\n"
                "3. Find the EXACT lines in the current code responsible for that wrong behaviour\n"
                "4. Write the minimum change needed to fix it without breaking passing tests\n"
                "5. Then output the COMPLETE corrected code in ONE ```python block\n\n"
                "STRICT OUTPUT RULE: The ```python block must be the LAST thing in your response."
            )),
            HumanMessage(content=(
                f"TASK REQUIREMENTS (source of truth):\n{state['task']}\n\n"
                f"CURRENT CODE:\n```python\n{state['code']}\n```\n\n"
                f"FAILURE ANALYSIS (debug attempt {iteration}/{MAX_ITERATIONS}):\n"
                f"{failure_summary}\n\n"
                "Step through each failure, identify the root cause, then write the corrected ```python code:"
            )),
        ])

        code = _extract_code(resp.content)
        workspace = Path(state["workspace"])
        (workspace / "solution.py").write_text(code)

        # Capture the model's reasoning (everything before the code block) for the proof
        reasoning = resp.content.split("```python")[0].strip()
        reasoning_snippet = reasoning[:400] + "..." if len(reasoning) > 400 else reasoning

        t1 = time.time()
        return {
            "code": code,
            "iteration": iteration,
            "logs": [_log(
                "DEBUGGER", t0, t1,
                f"**Attempt {iteration}/{MAX_ITERATIONS}**\n\n"
                f"**Root cause analysis:**\n{reasoning_snippet}\n\n"
                f"Patched solution.py ({len(code.splitlines())} lines)"
            )],
        }
    return debugger


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def build_pipeline(model: BaseChatModel):
    def route_after_eval(state: CodingState) -> str:
        if state["passed"]:
            return END
        if state["iteration"] >= MAX_ITERATIONS:
            return END
        return "debugger"

    g = StateGraph(CodingState)
    g.add_node("planner", make_planner(model))
    g.add_node("coder", make_coder(model))
    g.add_node("evaluator", make_evaluator())
    g.add_node("debugger", make_debugger(model))

    g.add_edge(START, "planner")
    g.add_edge("planner", "coder")
    g.add_edge("coder", "evaluator")
    g.add_conditional_edges("evaluator", route_after_eval)
    g.add_edge("debugger", "evaluator")

    return g.compile()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_task(
    task: str,
    tests_path: str,
    model: BaseChatModel,
    workspace_dir: Path | None = None,
) -> CodingState:
    workspace = workspace_dir or Path("workspace") / f"run_{int(time.time())}"
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "solution.py").write_text("# placeholder\n")

    initial: CodingState = {
        "task": task,
        "workspace": str(workspace),
        "tests_path": str(Path(tests_path).resolve()),
        "plan": "",
        "code": "",
        "test_output": "",
        "passed": None,
        "iteration": 0,
        "t_start": time.time(),
        "logs": [],
    }
    pipeline = build_pipeline(model)
    return pipeline.invoke(initial, {"recursion_limit": 30})
