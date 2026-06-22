"""
build_agent(model, rung, task_dir) → CompiledStateGraph

The Harness Ladder — each rung adds one component and makes the system more reliable:

  Rung 0  Bare ReAct loop — model + tools, no scaffolding
  Rung 1  + Planning  — agent is prompted + has plan tools (structure helps even dumb models)
  Rung 2  + Memory    — scratch scratchpad offloads working memory from the context window
  Rung 3  + Verify    — harness auto-runs tests after agent stops; re-injects failures into loop
                        KEY LESSON: the harness enforces the feedback loop, the model doesn't choose it
  Rung 4  + Sandbox   — tool middleware blocks writes to anything except solution.py
                        Ashby's Law: restricting bad moves is cheaper than asking the model to avoid them
  Rung 5  + Sub-agents — delegate_subtask spawns isolated context for research/sub-problems

Graph shape:
  Rung 0-2:   START → agent → (tool_calls?) → tools → agent → ... → END
  Rung 3-5:   START → agent → (tool_calls?) → tools → agent
                                             → (done?)    → verify → (passed?) → END
                                                                    → (failed?) → agent
"""
import subprocess
from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode

from harness.state import AgentState
from tools.factory import get_tools

MAX_VERIFY_ATTEMPTS = 3
RECURSION_LIMIT = 60

SYSTEM_PROMPTS = {
    0: (
        "You are a coding agent. Use your tools to complete the task.\n"
        "Start by reading description.md to understand the requirements.\n"
        "Write your implementation to solution.py.\n"
        "Call run_tests to check your work before finishing."
    ),
    1: (
        "You are a coding agent with planning capability.\n"
        "FIRST: call create_plan to decompose the task into concrete steps.\n"
        "THEN: execute each step, calling mark_step_done as you complete them.\n"
        "Start by reading description.md. Write your implementation to solution.py."
    ),
    2: (
        "You are a coding agent with planning and scratch memory.\n"
        "FIRST: call create_plan to decompose the task.\n"
        "Use scratch_write to record edge cases, algorithm choices, and notes before coding.\n"
        "Use scratch_read to recall your notes when you need them.\n"
        "Start by reading description.md. Write your implementation to solution.py."
    ),
    3: (
        "You are a coding agent. The harness automatically runs tests when you stop calling tools.\n"
        "If tests fail, you will see the output and must fix solution.py.\n"
        "FIRST: call create_plan. Use scratch for notes.\n"
        "Start by reading description.md. Write your implementation to solution.py."
    ),
    4: (
        "You are a coding agent in a sandboxed environment.\n"
        "SANDBOX RULE: you may ONLY write to solution.py — all other writes are rejected.\n"
        "FIRST: call create_plan. Use scratch for notes.\n"
        "Start by reading description.md."
    ),
    5: (
        "You are an orchestrating coding agent.\n"
        "For complex sub-problems, use delegate_subtask to get specialist analysis.\n"
        "FIRST: call create_plan. Use scratch for notes. Use delegate_subtask for research.\n"
        "Start by reading description.md. Write your final implementation to solution.py."
    ),
}


def build_agent(model: BaseChatModel, rung: int, task_dir: Path):
    """Return a compiled LangGraph agent at the given harness rung."""
    task_dir = Path(task_dir)
    tools = get_tools(rung, task_dir, model)
    tool_node = ToolNode(tools)
    system_prompt = SYSTEM_PROMPTS[min(rung, 5)]
    bound_model = model.bind_tools(tools)

    # ------------------------------------------------------------------
    # Node: agent — single LLM call
    # ------------------------------------------------------------------
    def agent_node(state: AgentState) -> dict:
        messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
        response = bound_model.invoke(messages)
        return {"messages": [response]}

    # ------------------------------------------------------------------
    # Edge: should_continue — after the agent node decides what to do next
    # ------------------------------------------------------------------
    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        has_tool_calls = bool(getattr(last, "tool_calls", None))
        if has_tool_calls:
            return "tools"
        # No tool calls = agent signals it's done
        if rung >= 3:
            return "verify"
        return END

    # ------------------------------------------------------------------
    # Node: verify (rung 3+) — run tests; re-inject failures
    # The harness owns this node; the model has no say in whether it runs.
    # ------------------------------------------------------------------
    def verify_node(state: AgentState) -> dict:
        test_file = task_dir / "test_solution.py"
        solution_file = task_dir / "solution.py"

        if not solution_file.exists():
            return {
                "messages": [HumanMessage(content="solution.py not found. Write your implementation first.")],
                "verify_attempts": state.get("verify_attempts", 0) + 1,
                "passed": False,
            }

        result = subprocess.run(
            ["python", "-m", "pytest", str(test_file), "-v", "--tb=short", "--no-header"],
            capture_output=True,
            text=True,
            cwd=str(task_dir),
            timeout=30,
        )
        output = (result.stdout + result.stderr).strip()
        passed = result.returncode == 0

        if passed:
            return {"passed": True}

        attempts = state.get("verify_attempts", 0) + 1
        feedback = (
            f"Tests failed (attempt {attempts}/{MAX_VERIFY_ATTEMPTS}):\n\n"
            f"{output}\n\n"
            "Fix the failing tests in solution.py and stop calling tools when done."
        )
        return {
            "messages": [HumanMessage(content=feedback)],
            "verify_attempts": attempts,
            "passed": False,
        }

    # ------------------------------------------------------------------
    # Edge: verify_router — after verify, decide whether to continue
    # ------------------------------------------------------------------
    def verify_router(state: AgentState) -> str:
        if state.get("passed"):
            return END
        if state.get("verify_attempts", 0) >= MAX_VERIFY_ATTEMPTS:
            return END
        return "agent"

    # ------------------------------------------------------------------
    # Assemble the graph
    # ------------------------------------------------------------------
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")

    if rung >= 3:
        graph.add_node("verify", verify_node)
        graph.add_conditional_edges("verify", verify_router)

    return graph.compile()
