"""Subagents: small ReAct loops, each bound to tools exposed by one MCP server.

This mirrors the "supervisor -> subagent -> tools/MCP" shape from a real
backend: each subagent has its own tool surface and makes its own tool-calling
decisions, independent of the supervisor. We build them fresh per request
(cheap: stdio MCP servers, in-process) so each demo run is self-contained;
in a long-lived service you'd instead build these once at startup and reuse
the MultiServerMCPClient/agent objects across requests.
"""
from __future__ import annotations

import os

from langchain.agents import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

from agents.network_client import wrap_tools_with_retry
from llm import get_chat_model

_HERE = os.path.dirname(os.path.abspath(__file__))
_SERVERS_DIR = os.path.join(os.path.dirname(_HERE), "mcp_servers")

OPS_AGENT_PROMPT = (
    "You are the ops subagent. You handle order status, refunds, and arithmetic "
    "needed to compute refund amounts. Use your tools; do not guess order data. "
    "If a tool call fails, report the failure plainly instead of pretending it succeeded."
)

SUPPORT_AGENT_PROMPT = (
    "You are the support subagent. You answer policy questions and look up "
    "support tickets using your tools. Do not answer from memory if a tool can confirm it."
)

NETWORK_AGENT_PROMPT = (
    "You are the network subagent. You run CLI commands on network devices, "
    "resolve DNS names, and check reachability with ping. Use your tools; do not "
    "guess device output. When run_commands returns per-device results, check each "
    "one -- a batch call can succeed overall while individual devices in it failed. "
    "Likewise, ping_check returning 100% loss for a host is a real outage, not an "
    "error to ignore just because the tool call itself succeeded. If a tool call "
    "fails outright, report the failure plainly instead of pretending it succeeded."
)


async def _load_tools(server_name: str, script: str):
    client = MultiServerMCPClient(
        {
            server_name: {
                "command": "python",
                "args": [os.path.join(_SERVERS_DIR, script)],
                "transport": "stdio",
            }
        }
    )
    return await client.get_tools()


async def _build_agent(server_name: str, script: str, system_prompt: str):
    tools = await _load_tools(server_name, script)
    model = get_chat_model()
    return create_react_agent(model, tools, prompt=system_prompt)


async def build_ops_agent():
    return await _build_agent("ops", "ops_server.py", OPS_AGENT_PROMPT)


async def build_support_agent():
    return await _build_agent("knowledge", "knowledge_server.py", SUPPORT_AGENT_PROMPT)


async def build_network_agent(*, traced_retries: bool = False):
    """traced_retries controls how the retry loop around each network tool
    call is instrumented -- see agents/network_client.py. Run the same
    flaky-device scenario with both settings to see the difference in
    Langfuse directly."""
    tools = await _load_tools("network", "network_server.py")
    tools = wrap_tools_with_retry(tools, traced=traced_retries)
    model = get_chat_model()
    return create_react_agent(model, tools, prompt=NETWORK_AGENT_PROMPT)
