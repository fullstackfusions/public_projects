"""
Generic Agent base class.

Subclass this and provide:
- name / description / system_prompt
- (optional) mcp_server_url + mcp_server_name to load MCP tools at runtime
- (optional) override get_extra_tools() to inject additional LangChain tools

Each agent:
  - builds a LangGraph create_react_agent graph with its tools
  - applies middleware: concurrency limit, retry with back-off, structured logging
  - exposes itself as a LangChain StructuredTool via as_tool()
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from app.config import get_settings

logger = logging.getLogger(__name__)


class BaseAgent(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    system_prompt: str

    # MCP server config — set in subclasses via field defaults.
    # SSE transport: set mcp_server_url.
    mcp_server_url: str | None = None
    mcp_server_name: str | None = None
    # stdio transport: set mcp_command + mcp_args (+ optional mcp_env overrides).
    mcp_command: str | None = None
    mcp_args: list[str] = Field(default_factory=list)
    mcp_env: dict[str, str] = Field(default_factory=dict)

    # LLM config — falls back to settings when left empty.
    llm_provider: str = ""
    model_name: str = ""

    # Middleware config
    max_retries: int = 3
    max_concurrent: int = 5

    # Lazily initialised in model_post_init
    _semaphore: asyncio.Semaphore = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

    # ------------------------------------------------------------------
    # LLM factory
    # ------------------------------------------------------------------

    def _get_llm(self) -> BaseChatModel:
        settings = get_settings()
        provider = self.llm_provider or settings.default_llm_provider
        model = self.model_name or settings.default_model

        if provider == "anthropic":
            return ChatAnthropic(model_name=model, api_key=settings.anthropic_api_key, timeout=300, stop=None)
        return ChatOpenAI(model=model, api_key=settings.openai_api_key)

    # ------------------------------------------------------------------
    # Tool factories
    # ------------------------------------------------------------------

    async def get_extra_tools(self) -> list:
        """Override in subclasses to inject non-MCP LangChain tools."""
        return []

    # ------------------------------------------------------------------
    # Graph builder
    # ------------------------------------------------------------------

    def _build_graph(self, tools: list):
        return create_react_agent(
            model=self._get_llm(),
            tools=tools,
            prompt=SystemMessage(content=self.system_prompt),
        )

    # ------------------------------------------------------------------
    # MCP connection config
    # ------------------------------------------------------------------

    def _mcp_server_config(self) -> dict[str, Any] | None:
        """Build the MultiServerMCPClient config for this agent.

        Returns ``None`` when no MCP server is configured. stdio transport
        takes precedence over SSE when both are set.
        """
        server_name = self.mcp_server_name or self.name.lower().replace(" ", "_")
        if self.mcp_command:
            return {
                server_name: {
                    "command": self.mcp_command,
                    "args": self.mcp_args,
                    "transport": "stdio",
                    "env": {**os.environ, **self.mcp_env},
                }
            }
        if self.mcp_server_url:
            return {server_name: {"url": self.mcp_server_url, "transport": "sse"}}
        return None

    # ------------------------------------------------------------------
    # Graph invocation
    # ------------------------------------------------------------------

    async def _invoke_graph(self, graph, query: str, thread_id: str) -> str:
        config = {"configurable": {"thread_id": thread_id}}
        result = await graph.ainvoke(
            {"messages": [("human", query)]},
            config=config,
        )
        return result["messages"][-1].content

    # ------------------------------------------------------------------
    # Public run — with middleware: semaphore + retry + logging
    # ------------------------------------------------------------------

    async def run(
        self,
        query: str,
        thread_id: str = "default",
        status_callback: Callable[..., Awaitable[None]] | None = None,
    ) -> str:
        if status_callback:
            await status_callback(self.name, "started", query[:120])

        async def _execute() -> str:
            extra_tools = await self.get_extra_tools()
            server_config = self._mcp_server_config()
            if server_config is None:
                tools = extra_tools
            else:
                mcp_client = MultiServerMCPClient(server_config)
                tools = (await mcp_client.get_tools()) + extra_tools
            graph = self._build_graph(tools)
            return await self._invoke_graph(graph, query, thread_id)

        last_exc: Exception | None = None

        async with self._semaphore:
            for attempt in range(self.max_retries):
                try:
                    result = await _execute()
                    logger.info("Agent %s completed (attempt %d)", self.name, attempt + 1)
                    if status_callback:
                        await status_callback(self.name, "completed", None)
                    return result
                except Exception as exc:
                    # Unwrap ExceptionGroup (raised by asyncio.TaskGroup inside
                    # MultiServerMCPClient.get_tools) to surface the real cause.
                    if isinstance(exc, ExceptionGroup) and exc.exceptions:
                        last_exc = exc.exceptions[0]
                    else:
                        last_exc = exc
                    logger.warning(
                        "Agent %s failed attempt %d/%d: %s",
                        self.name,
                        attempt + 1,
                        self.max_retries,
                        exc,
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2**attempt)

        if status_callback:
            await status_callback(self.name, "error", str(last_exc))
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Expose as LangChain tool (for use by a parent agent)
    # ------------------------------------------------------------------

    def as_tool(
        self,
        status_callback: Callable[..., Awaitable[None]] | None = None,
    ) -> StructuredTool:
        async def _invoke(query: str) -> str:
            return await self.run(
                query=query,
                thread_id="tool_call",
                status_callback=status_callback,
            )

        return StructuredTool.from_function(
            coroutine=_invoke,
            name=self.name,
            description=self.description,
        )
