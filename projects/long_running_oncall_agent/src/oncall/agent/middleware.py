"""Project middleware: measurement probe, deterministic log folding, summarizers.

The stock `langchain-scaledown` middlewares are used unmodified; everything here
either measures them or fills a gap the bench exposed (log folding).
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Sequence
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage, get_buffer_string
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_scaledown import ScaledownAPIError, ScaledownSummarizer

from oncall import db, telemetry


def _preview(text: str, n: int = 240) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n] + "…"


class ModelProbeMiddleware(AgentMiddleware):
    """Innermost model wrapper: measures exactly what reaches the agent model.

    Because it sits inside summarization and tool-schema augmentation, its token
    counts reflect the request after every context-management step has run.
    """

    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelResponse:
        ctx = telemetry.current()
        if ctx is None:
            return handler(request)
        ctx.step += 1
        if ctx.step == 1:
            self._persist_extraction(ctx, request)

        msgs: list[BaseMessage] = [*([request.system_message] if request.system_message else []),
                                   *request.messages]
        self._flag_placeholder_summary(ctx, request.messages)
        msg_tokens = sum(telemetry.count_tokens(m.text) for m in msgs)
        tool_tokens = sum(
            telemetry.count_tokens(json.dumps(convert_to_openai_tool(t))) for t in request.tools
        )
        t0 = time.perf_counter()
        response = handler(request)
        latency = (time.perf_counter() - t0) * 1000

        ai = next((m for m in reversed(response.result) if isinstance(m, AIMessage)), None)
        usage = (ai.usage_metadata or {}) if ai else {}
        meta = (ai.response_metadata or {}) if ai else {}
        tool_calls = [{"name": c["name"], "args": c["args"]} for c in (ai.tool_calls if ai else [])]
        # Generated output = visible text + tool-call JSON (a tool-only turn has empty text).
        out_text = (ai.text if ai else "") + (json.dumps(tool_calls) if tool_calls else "")
        ctx.record(
            "agent_model",
            in_chars=sum(len(m.text) for m in msgs),
            out_chars=len(out_text),
            in_tokens=msg_tokens + tool_tokens,
            out_tokens=telemetry.count_tokens(out_text),
            latency_ms=latency,
            meta={
                "messages": len(msgs),
                "tool_schema_tokens": tool_tokens,
                # Ollama's own counters. prompt_eval_count excludes KV-cache hits, so it is
                # the compute actually spent, not the context size.
                "ollama_prompt_eval_count": usage.get("input_tokens"),
                "ollama_eval_count": usage.get("output_tokens"),
                "ollama_prompt_eval_ms": (meta.get("prompt_eval_duration") or 0) / 1e6,
                "ollama_eval_ms": (meta.get("eval_duration") or 0) / 1e6,
                "tool_calls": [c["name"] for c in tool_calls],
            },
        )
        ctx.emit(
            "model_call",
            step=ctx.step,
            context_tokens=msg_tokens + tool_tokens,
            latency_ms=round(latency),
            tool_calls=[{"name": c["name"], "args": _preview(json.dumps(c["args"]), 300)}
                        for c in tool_calls],
            text=_preview(ai.text if ai else ""),
        )
        return response

    _PLACEHOLDERS = ("Previous conversation was too long to summarize.",
                     "No previous conversation history.")

    def _flag_placeholder_summary(self, ctx: telemetry.RunContext, messages: list) -> None:
        """LangChain substitutes a fixed string when trimming leaves nothing to summarize.
        It raises nothing, so make it loud: once per distinct summary message."""
        for m in messages:
            if (m.additional_kwargs or {}).get("lc_source") != "summarization":
                continue
            hit = next((p for p in self._PLACEHOLDERS if p in m.text), None)
            key = f"placeholder:{m.id or hash(m.text)}"
            if hit and key not in ctx.counters:
                ctx.counters[key] = 1
                ctx.record("summary_placeholder", ok=False, meta={"text": hit})
                ctx.emit("summary_placeholder", text=hit,
                         note="history was replaced by a placeholder, not a summary")

    @staticmethod
    def _persist_extraction(ctx: telemetry.RunContext, request: ModelRequest) -> None:
        record = (request.state or {}).get("scaledown_extraction")
        if record:
            fields = record.get("fields", {})
            db.set_extraction(ctx.run_id, fields)
            ctx.emit("extraction", fields=fields)


class ToolResultProbeMiddleware(AgentMiddleware):
    """Outer tool wrapper: reports each tool result as the model will see it, i.e. after
    folding and compression (the raw size is recorded by the tool itself)."""

    def wrap_tool_call(self, request, handler):
        result = handler(request)
        if isinstance(result, ToolMessage):
            telemetry.emit(
                "tool_result",
                tool=request.tool_call["name"],
                chars=len(result.text),
                tokens=telemetry.count_tokens(result.text),
                preview=_preview(result.text, 400),
            )
        return result


# --- Deterministic log folding -------------------------------------------------------

_LOG_LINE = re.compile(r"^(?P<ts>\S+)\s+(?P<level>[A-Z]+)\s+(?P<svc>\S+)\s+(?P<msg>.*)$")
_HAS_DIGIT = re.compile(r"\d")
_HEX_ID = re.compile(r"^[0-9a-f]{8,}$|^[0-9a-f]{8}-[0-9a-f-]{27}$")


def _template(msg: str) -> str:
    """Drain-style masking: a whitespace token containing a digit (or a hex id) is a
    variable. Generic on purpose, so it is not tuned to any one log format."""
    return " ".join("<*>" if _HAS_DIGIT.search(t) or _HEX_ID.match(t) else t
                    for t in msg.split())


def fold_logs(text: str) -> str:
    """Collapse log lines that differ only in ids/numbers into one exemplar + count.

    Every distinct template survives with its first verbatim example, so exact error
    strings (what an engineer greps for) are never lost; only repetition is.
    """
    header: list[str] = []
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            header.append(line)
            continue
        m = _LOG_LINE.match(line)
        # Unknown formats (e.g. LogHub corpora) fold on the whole line's template.
        key = (m["level"], m["svc"], _template(m["msg"])) if m else ("", "", _template(line))
        ts = m["ts"] if m else ""
        g = groups.get(key)
        if g is None:
            groups[key] = {"first": ts, "last": ts, "n": 1, "example": line}
        else:
            g["n"] += 1
            g["last"] = ts
    total = sum(g["n"] for g in groups.values())
    out = [*header, f"# log_fold: {total} lines -> {len(groups)} distinct templates "
                    "(count, first..last, first verbatim example)"]
    for g in groups.values():
        span = g["first"] if g["n"] == 1 else f"{g['first']}..{g['last']}"
        out.append(f"[x{g['n']} {span}] {g['example']}" if span else f"[x{g['n']}] {g['example']}")
    return "\n".join(out)


class LogFoldMiddleware(AgentMiddleware):
    """Fold `query_logs` output before anything else (including ScaleDown) sees it."""

    def __init__(self, tools: Sequence[str] = ("query_logs",)) -> None:
        super().__init__()
        self.tool_names = set(tools)

    def wrap_tool_call(self, request, handler):
        result = handler(request)
        if (
            request.tool_call["name"] not in self.tool_names
            or not isinstance(result, ToolMessage)
            or not result.text.startswith("# logs")
        ):
            return result
        raw = result.text
        t0 = time.perf_counter()
        folded = fold_logs(raw)
        if len(folded) >= len(raw):  # tiny/empty results: the fold header would only add bytes
            return result
        telemetry.record(
            "log_fold",
            in_chars=len(raw),
            out_chars=len(folded),
            in_tokens=telemetry.count_tokens(raw),
            out_tokens=telemetry.count_tokens(folded),
            latency_ms=(time.perf_counter() - t0) * 1000,
        )
        return result.model_copy(update={"content": folded})


# --- Summarizers -------------------------------------------------------------------------


def _as_text(value: str | Sequence[BaseMessage]) -> str:
    return value if isinstance(value, str) else get_buffer_string(value)


def local_summarizer(model, prompt_template: str) -> Runnable:
    """Summarize with the agent's own model, as Deep Agents does by default — but measured."""

    def run(value: str | Sequence[BaseMessage]) -> str:
        text = _as_text(value)
        prompt = prompt_template.replace("{messages}", text)
        t0 = time.perf_counter()
        ai = model.invoke(prompt)
        usage = ai.usage_metadata or {}
        telemetry.record(
            "local_summarize",
            in_chars=len(prompt),
            out_chars=len(ai.text),
            in_tokens=telemetry.count_tokens(prompt),
            out_tokens=telemetry.count_tokens(ai.text),
            latency_ms=(time.perf_counter() - t0) * 1000,
            meta={"ollama_prompt_eval_count": usage.get("input_tokens")},
        )
        telemetry.emit("summarized", by="local", in_tokens=telemetry.count_tokens(prompt),
                       out_tokens=telemetry.count_tokens(ai.text))
        return ai.text.strip()

    return RunnableLambda(run, name="local_summarizer")


def scaledown_summarizer(client, fallback: Runnable) -> Runnable:
    """ScaleDown summarizer with a local fallback.

    Inside Deep Agents, a summarizer exception propagates out of the model call
    (unlike `ScaledownSummarizationMiddleware`, which fails open). The fallback keeps
    a long-running job alive if ScaleDown is unavailable; the ledger shows which ran.
    """
    sd = ScaledownSummarizer(client=client)

    def run(value: str | Sequence[BaseMessage]) -> str:
        summary = sd.invoke(value)
        telemetry.emit("summarized", by="scaledown", out_tokens=telemetry.count_tokens(summary))
        return summary

    return RunnableLambda(run, name="scaledown_summarizer").with_fallbacks(
        [fallback], exceptions_to_handle=(ScaledownAPIError,)
    )
