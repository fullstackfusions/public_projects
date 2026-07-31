"""Retry wrapping for the network_agent's MCP tools, in two flavors that
produce very different Langfuse traces for the exact same underlying flakiness:

- `traced=False` ("opaque"): a plain try/except retry loop, same as what an
  enterprise LLM gateway's SDK typically does under the hood. LangChain only
  ever sees ONE tool call start/end -- the retries happen invisibly inside
  it. In Langfuse this shows up as a single tool span whose duration is
  inflated by however many silent attempts it took, with no way to tell "1
  slow attempt" from "3 dropped connections then a fast one" without adding
  your own logging elsewhere.

- `traced=True`: the identical retry loop, except each attempt gets its own
  Langfuse span (`gateway-attempt-N`) nested under the tool call, with its
  own status and error. Same retry behavior, completely different
  observability -- which is the point of this module.

This is the fix for the blind spot: retries have to be visible to the
tracing layer, either by living above it (LangChain-native `.with_retry()`)
or, when that's not possible because the retry lives inside a vendored
gateway/MCP client, by manually spanning each attempt like `_retry_traced`
does here.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, List

from langchain_core.tools import BaseTool, StructuredTool

from observability.langfuse_setup import get_langfuse_client

MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = 0.05


async def _retry_opaque(coro_fn: Callable[..., Coroutine], **kwargs) -> Any:
    last_exc: Exception | None = None
    for _attempt in range(1, MAX_RETRIES + 1):
        try:
            return await coro_fn(**kwargs)
        except Exception as exc:  # noqa: BLE001 - re-raised below once retries are exhausted
            last_exc = exc
            await asyncio.sleep(_RETRY_BACKOFF_SECONDS)
    assert last_exc is not None
    raise last_exc


async def _retry_traced(coro_fn: Callable[..., Coroutine], **kwargs) -> Any:
    client = get_langfuse_client()
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        with client.start_as_current_span(
            name=f"gateway-attempt-{attempt}", input=kwargs
        ) as span:
            try:
                result = await coro_fn(**kwargs)
                span.update(output=result)
                return result
            except Exception as exc:  # noqa: BLE001 - recorded on the span, then retried/raised
                last_exc = exc
                span.update(level="ERROR", status_message=f"{type(exc).__name__}: {exc}")
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS)
    assert last_exc is not None
    raise last_exc


def _wrap_tool(tool: BaseTool, traced: bool) -> BaseTool:
    if tool.coroutine is None:
        # No async implementation to wrap around -- leave the tool as-is.
        return tool

    original_coroutine = tool.coroutine
    retry_runner = _retry_traced if traced else _retry_opaque

    async def wrapped(**kwargs: Any) -> Any:
        return await retry_runner(original_coroutine, **kwargs)

    return StructuredTool.from_function(
        name=tool.name,
        description=tool.description,
        args_schema=tool.args_schema,
        coroutine=wrapped,
    )


def wrap_tools_with_retry(tools: List[BaseTool], *, traced: bool) -> List[BaseTool]:
    """Wrap every tool so calls get up to MAX_RETRIES attempts on failure.
    `traced=True` gives each attempt its own Langfuse span; `traced=False`
    (the default most gateway SDKs give you for free) does not."""
    return [_wrap_tool(tool, traced=traced) for tool in tools]
