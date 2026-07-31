"""Local WebSocket server: streams the supervisor graph's live progress
(routing decisions, tool calls, tokens) instead of leaving the frontend to
poll blind and guess at a timeout.

Run:
    uvicorn server:app --reload --port 8000
Then open http://localhost:8000/ in a browser.

One WebSocket connection = one conversation thread. Client -> server
messages (JSON, one per WS frame):
    {"type": "query",  "text": "..."}          start a run, or -- if one is
                                                already in flight -- queue this
                                                as mid-flight steering input
    {"type": "cancel", "mode": "soft"}         stop at the next supervisor hop
                                                (default; safe for in-flight
                                                side-effecting tool calls)
    {"type": "cancel", "mode": "hard"}         cancel immediately, mid-call
                                                (fine for read-only tools,
                                                risky for e.g. a refund call)

Server -> client messages:
    {"type": "event", "kind": "node_start"|"node_end"|"tool_start"|"tool_end"|"token"|"steered", "node": ..., "data": ...}
    {"type": "final", "text": "..."}
    {"type": "cancelled"}
    {"type": "error", "message": "..."}
"""
from __future__ import annotations

import asyncio
import json

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from langchain_core.messages import HumanMessage

load_dotenv()

from agents.subagents import build_network_agent, build_ops_agent, build_support_agent  # noqa: E402
from agents.supervisor import build_supervisor_graph  # noqa: E402
from observability.langfuse_setup import score_trace, traced_request  # noqa: E402

app = FastAPI()

_GRAPH_NODES = {"supervisor", "ops_agent", "support_agent", "network_agent"}

_graph = None
_graph_lock = asyncio.Lock()


async def get_graph():
    """Built once per process and reused across WebSocket connections --
    same as a long-lived agent service would, not rebuilt per request."""
    global _graph
    async with _graph_lock:
        if _graph is None:
            ops_agent = await build_ops_agent()
            support_agent = await build_support_agent()
            # traced_retries=True here so the live feed shows each gateway
            # attempt as its own event -- flip to False to see the opaque
            # version streamed instead.
            network_agent = await build_network_agent(traced_retries=True)
            _graph = build_supervisor_graph(ops_agent, support_agent, network_agent)
    return _graph


def _serialize_event(event: dict) -> dict | None:
    kind = event["event"]
    name = event.get("name", "")

    if kind == "on_chat_model_stream":
        chunk = event["data"].get("chunk")
        text = getattr(chunk, "content", "") if chunk else ""
        if not text:
            return None
        return {"type": "event", "kind": "token", "node": name, "data": text}

    if kind == "on_tool_start":
        return {"type": "event", "kind": "tool_start", "node": name, "data": event["data"].get("input")}

    if kind == "on_tool_end":
        return {"type": "event", "kind": "tool_end", "node": name, "data": str(event["data"].get("output"))}

    if kind == "on_chain_start" and name in _GRAPH_NODES:
        return {"type": "event", "kind": "node_start", "node": name, "data": None}

    if kind == "on_chain_end" and name in _GRAPH_NODES:
        return {"type": "event", "kind": "node_end", "node": name, "data": None}

    return None


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    thread_id = f"live-{id(websocket)}"
    steering_queue: asyncio.Queue = asyncio.Queue()
    cancel_soft = asyncio.Event()
    run_task: asyncio.Task | None = None

    async def run_graph(query: str) -> None:
        graph = await get_graph()
        final_text = None

        with traced_request(
            "agent_request", query=query, session_id=thread_id, tags=["live-stream"]
        ) as (_handler, base_config, trace_id):
            config = {
                **base_config,
                "configurable": {
                    **base_config.get("configurable", {}),
                    "steering_queue": steering_queue,
                    "cancel_event": cancel_soft,
                },
                "recursion_limit": 20,
            }
            try:
                async for event in graph.astream_events(
                    {"messages": [HumanMessage(content=query)], "hops": 0},
                    config=config,
                    version="v2",
                ):
                    payload = _serialize_event(event)
                    if payload:
                        await websocket.send_json(payload)

                    if event["event"] == "on_chain_end" and event.get("name") in (
                        "ops_agent",
                        "support_agent",
                        "network_agent",
                    ):
                        output = event["data"].get("output") or {}
                        msgs = output.get("messages")
                        if msgs:
                            final_text = msgs[-1].content

                if cancel_soft.is_set():
                    await websocket.send_json({"type": "cancelled"})
                    score_trace(trace_id, "task_success", 0.0, comment="soft-cancelled by user")
                else:
                    await websocket.send_json({"type": "final", "text": final_text or ""})
                    score_trace(trace_id, "task_success", 1.0, comment="completed")
            except asyncio.CancelledError:
                await websocket.send_json({"type": "cancelled"})
                score_trace(trace_id, "task_success", 0.0, comment="hard-cancelled by user")
                raise
            except Exception as exc:  # noqa: BLE001 - reported to the client, not swallowed
                await websocket.send_json({"type": "error", "message": f"{type(exc).__name__}: {exc}"})
                score_trace(trace_id, "task_success", 0.0, comment=str(exc))

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg["type"] == "query":
                if run_task and not run_task.done():
                    # A run is already in flight -- this is mid-flight
                    # steering input, not a new independent request. It'll
                    # be picked up at the next supervisor hop.
                    await steering_queue.put(msg["text"])
                    await websocket.send_json(
                        {"type": "event", "kind": "steered", "node": "client", "data": msg["text"]}
                    )
                else:
                    cancel_soft.clear()
                    run_task = asyncio.create_task(run_graph(msg["text"]))

            elif msg["type"] == "cancel" and run_task and not run_task.done():
                if msg.get("mode") == "hard":
                    run_task.cancel()
                else:
                    cancel_soft.set()

    except WebSocketDisconnect:
        if run_task and not run_task.done():
            run_task.cancel()
