"""CLI entrypoint.

    python run.py "What's your return policy?"
    python run.py --demo        # runs 4 scripted scenarios, incl. one failure
    python run.py --demo --user alice --session s-42

Every run opens exactly one Langfuse trace for the whole request (supervisor
hops + subagent tool calls all nest under it) and prints the trace URL so you
can jump straight to it in the UI.
"""
from __future__ import annotations

import argparse
import asyncio
import uuid

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.panel import Panel

load_dotenv()

from agents.subagents import build_ops_agent, build_support_agent  # noqa: E402
from agents.supervisor import build_supervisor_graph  # noqa: E402
from observability.langfuse_setup import flush, score_trace, traced_request, trace_url  # noqa: E402

console = Console()

DEMO_SCENARIOS = [
    {
        "label": "single-hop policy question",
        "query": "What's your return policy?",
    },
    {
        "label": "single-hop ops question",
        "query": "What's the status of order ORD-100?",
    },
    {
        "label": "multi-hop: policy then refund (supervisor hands off twice)",
        "query": (
            "Can you confirm our return policy applies to order ORD-200, "
            "and if so refund the full $129.50?"
        ),
    },
    {
        "label": "deliberate failure: refund on a flagged order",
        "query": "Please refund the full amount for order ORD-999.",
    },
]


async def run_once(graph, query: str, *, session_id: str, user_id: str | None, tags: list[str]) -> None:
    console.print(Panel(query, title="query", border_style="cyan"))

    with traced_request(
        "agent_request", query=query, session_id=session_id, user_id=user_id, tags=tags
    ) as (handler, config, trace_id):
        try:
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=query)], "hops": 0}, config=config
            )
            final_message = result["messages"][-1].content
            console.print(Panel(str(final_message), title="response", border_style="green"))
            score_trace(trace_id, "task_success", 1.0, comment="graph completed without error")
        except Exception as exc:  # noqa: BLE001 - intentionally shown to the user, not swallowed
            console.print(Panel(f"{type(exc).__name__}: {exc}", title="error", border_style="red"))
            score_trace(trace_id, "task_success", 0.0, comment=str(exc))
        finally:
            flush()

    console.print(f"[bold]Langfuse trace:[/bold] {trace_url(trace_id)}\n")


async def build_graph():
    ops_agent = await build_ops_agent()
    support_agent = await build_support_agent()
    return build_supervisor_graph(ops_agent, support_agent)


async def run_demo(user_id: str | None) -> None:
    session_id = f"demo-{uuid.uuid4().hex[:8]}"
    console.print(f"[bold yellow]Demo session_id={session_id}[/bold yellow] "
                   "(open Langfuse -> Sessions to see all 4 traces grouped together)\n")
    graph = await build_graph()
    for scenario in DEMO_SCENARIOS:
        console.rule(scenario["label"])
        await run_once(
            graph,
            scenario["query"],
            session_id=session_id,
            user_id=user_id,
            tags=[scenario["label"].split(":")[0].strip().replace(" ", "-")],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="A single question to send through the supervisor.")
    parser.add_argument("--demo", action="store_true", help="Run the 4 scripted scenarios.")
    parser.add_argument("--session", default=None, help="Session id (defaults to a fresh uuid).")
    parser.add_argument("--user", default=None, help="User id attached to the trace(s).")
    args = parser.parse_args()

    if not args.demo and not args.query:
        parser.error("Provide a query, or pass --demo to run the scripted scenarios.")

    if args.demo:
        asyncio.run(run_demo(args.user))
    else:
        session_id = args.session or f"session-{uuid.uuid4().hex[:8]}"

        async def _single():
            graph = await build_graph()
            await run_once(graph, args.query, session_id=session_id, user_id=args.user, tags=["ad-hoc"])

        asyncio.run(_single())


if __name__ == "__main__":
    main()
