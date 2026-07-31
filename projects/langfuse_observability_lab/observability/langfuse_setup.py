"""Thin wrapper around the Langfuse Python SDK (v3, OTel-based).

Why a wrapper at all: the supervisor graph calls into subagent graphs as
plain Python function calls (`subgraph.invoke(...)` inside a node), and each
subagent in turn drives an MCP tool loop. Left alone, every one of those
`.invoke()` calls would start its *own* Langfuse trace instead of nesting
under one request. `start_as_current_span()` opens a root OTel span for the
whole request; because the SDK propagates that span via Python contextvars,
every LangChain run created underneath it (supervisor LLM, subagent LLM,
tool calls, MCP round-trips) nests under it automatically as long as the
*same* CallbackHandler instance is threaded through every `config=` — which
is exactly the same rule you'd apply across your real supervisor -> subagent
-> MCP chain.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from langfuse import get_client
from langfuse.langchain import CallbackHandler


def get_langfuse_client():
    """Singleton Langfuse client, configured from LANGFUSE_* env vars."""
    return get_client()


def new_callback_handler() -> CallbackHandler:
    """One handler per request. Pass the SAME instance into every nested
    graph/agent invoke() via config={"callbacks": [handler]} so all of it
    lands in one trace tree."""
    return CallbackHandler()


@contextmanager
def traced_request(
    name: str,
    *,
    query: str,
    session_id: str,
    user_id: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> Iterator[tuple["CallbackHandler", dict, str]]:
    """Open one root trace for an end-to-end request and yield
    (callback_handler, langgraph_config, trace_id).

    Pass `config` into every nested invoke() (supervisor graph, subagent
    graphs) so the whole call chain lands in this one trace.

    Usage:
        with traced_request("agent_request", query=q, session_id=sid) as (handler, config, trace_id):
            result = supervisor_graph.invoke({"messages": [...]}, config=config)
    """
    client = get_langfuse_client()
    handler = new_callback_handler()

    with client.start_as_current_span(name=name, input={"query": query}) as span:
        span.update_trace(
            session_id=session_id,
            user_id=user_id,
            tags=tags or [],
            metadata={"entrypoint": name},
        )
        config = {
            "callbacks": [handler],
            "metadata": {
                "langfuse_session_id": session_id,
                "langfuse_user_id": user_id,
                "langfuse_tags": tags or [],
            },
        }
        yield handler, config, span.trace_id


def score_trace(trace_id: str, name: str, value: float, comment: str | None = None) -> None:
    """Attach an evaluation score to a trace after the fact — e.g. a rule-based
    success/failure check, or the output of an LLM-as-judge run elsewhere."""
    client = get_langfuse_client()
    client.create_score(trace_id=trace_id, name=name, value=value, comment=comment)


def trace_url(trace_id: str) -> str:
    return get_langfuse_client().get_trace_url(trace_id=trace_id)


def flush() -> None:
    """Force-send buffered events. Call this before a short-lived script exits —
    otherwise the background batcher may not flush in time."""
    get_langfuse_client().flush()
