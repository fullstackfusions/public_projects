"""Supervisor graph: one LLM call per hop decides which subagent handles the
request next (or whether to finish), exactly like a supervisor node routing
to sub-agents/MCPs in a real backend. Subagents are themselves LLM-driven
tool-callers, so a single user query can produce a call chain several LLM
calls deep -- which is the whole reason this needs tracing, not eyeballing
logs.
"""
from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from llm import get_chat_model

MAX_HOPS = 4

SUPERVISOR_PROMPT = """You are the supervisor of a small support system.
You do not answer questions yourself. Each turn, read the conversation so far
and decide which subagent should act next, or whether the conversation is done:

- "ops_agent": order status, refunds, amount calculations.
- "support_agent": policy questions (returns, shipping, password reset), ticket lookups.
- "finish": the last subagent's message already answers the user; nothing more to do.

Route to exactly one subagent per turn. If the user's request has multiple
parts (e.g. a policy question AND a refund), route to one now and the other
on a later turn -- do not try to do both at once."""


class Route(BaseModel):
    agent: Literal["ops_agent", "support_agent", "finish"] = Field(
        description="Which subagent should act next, or 'finish' if done."
    )
    reason: str = Field(description="One sentence on why this route was chosen.")


class SupervisorState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    next: str
    hops: int


def build_supervisor_graph(ops_agent, support_agent):
    """ops_agent / support_agent are pre-built compiled subagent graphs
    (see agents.subagents) -- built once per process and reused across hops,
    same as you'd do with long-lived agent objects in a real service."""

    router_model = get_chat_model().with_structured_output(Route)

    async def supervisor_node(state: SupervisorState, config):
        hops = state.get("hops", 0)
        if hops >= MAX_HOPS:
            return {"next": "finish", "hops": hops}

        route = await router_model.ainvoke(
            [SystemMessage(SUPERVISOR_PROMPT), *state["messages"]], config=config
        )
        return {"next": route.agent, "hops": hops + 1}

    async def ops_node(state: SupervisorState, config):
        result = await ops_agent.ainvoke({"messages": state["messages"]}, config=config)
        return {"messages": [result["messages"][-1]]}

    async def support_node(state: SupervisorState, config):
        result = await support_agent.ainvoke({"messages": state["messages"]}, config=config)
        return {"messages": [result["messages"][-1]]}

    def route_from_supervisor(state: SupervisorState) -> str:
        return state["next"] if state["next"] != "finish" else END

    graph = StateGraph(SupervisorState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("ops_agent", ops_node)
    graph.add_node("support_agent", support_node)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {"ops_agent": "ops_agent", "support_agent": "support_agent", END: END},
    )
    # Both subagents report back to the supervisor, which decides whether to
    # finish or hand off again -- this is the "back and forth" that gets
    # hard to debug without per-hop tracing.
    graph.add_edge("ops_agent", "supervisor")
    graph.add_edge("support_agent", "supervisor")

    return graph.compile()
