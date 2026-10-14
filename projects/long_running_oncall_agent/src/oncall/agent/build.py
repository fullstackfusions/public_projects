"""Assemble the Deep Agent for one run from its profile flags."""

from __future__ import annotations

import httpx
import ollama
from deepagents import (
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    create_deep_agent,
    register_harness_profile,
)
from deepagents.backends import StateBackend
from deepagents.middleware.summarization import (
    DEEPAGENTS_DEFAULT_SUMMARY_PROMPT,
    SummarizationMiddleware,
)
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallLimitMiddleware,
    ModelRetryMiddleware,
)
from langchain_ollama import ChatOllama
from langchain_scaledown import ScaledownExtractionMiddleware, ScaledownToolCompressionMiddleware
from langgraph.checkpoint.base import BaseCheckpointSaver

from oncall import telemetry
from oncall.agent import guard as guard_mod
from oncall.agent.middleware import (
    LogFoldMiddleware,
    ModelProbeMiddleware,
    ToolResultProbeMiddleware,
    local_summarizer,
    scaledown_summarizer,
)
from oncall.agent.profiles import ProfileFlags
from oncall.agent.tools import ALL_TOOLS, BULKY_TOOLS
from oncall.config import settings

SYSTEM_PROMPT = """You are the on-call SRE agent for a production e-commerce platform.
An alert has fired. Investigate it with your tools and submit an incident report.

Method:
1. Read the alert. Identify the affected service and the time the incident started.
2. Look at the affected service's logs (prefer level=WARN or ERROR first), then follow
   upstream errors to the dependency that is actually failing.
3. Check recent deploys, config/flag changes and Kubernetes events around the start time.
4. Search the runbooks for the specific error you found.
5. Be skeptical of loud signals that do not explain the symptom in the alert.
6. Stop investigating as soon as you can name the specific change that caused it, and call
   `submit_incident_report` exactly once.

If a tool keeps failing, do not keep retrying it: use a different data source.
Do not ask the user questions; nobody is watching this run."""

# The loop trap (flaky-metrics-loop) is defused by this one sentence on qwen3:8b: the agent
# tries the failing tool twice and moves on. The "naive" variants drop exactly this
# sentence, so the guard can be tested against an agent that does retry.
RETRY_HINT = "If a tool keeps failing, do not keep retrying it: use a different data source.\n"
assert RETRY_HINT in SYSTEM_PROMPT
SYSTEM_PROMPTS = {"guarded": SYSTEM_PROMPT, "naive": SYSTEM_PROMPT.replace(RETRY_HINT, "")}

EXTRACTION_ENTITIES = {
    "service": "Name of the service the alert fires for",
    "region": "Cloud region of the incident",
    "started_at": "Time the incident started",
    "symptom": "The user-visible symptom or metric breach described in the alert",
    "severity": {"labels": ["SEV1", "SEV2", "SEV3"],
                 "description": "Severity level stated in the alert"},
    "incident_type": {"labels": ["error_rate", "latency", "login_failure", "data_staleness",
                                 "availability"]},
}

_registered = False


def _register_harness_profile() -> None:
    """No `task` subagent (its model calls would bypass the probe and go unmeasured) and no
    `execute` (no sandbox backend). Both also shrink the system prompt a CPU model prefills."""
    global _registered
    if not _registered:
        register_harness_profile("ollama", HarnessProfile(
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
            excluded_tools=frozenset({"execute"}),
        ))
        _registered = True


def agent_model() -> ChatOllama:
    s = settings()
    return ChatOllama(
        base_url=s.ollama_base_url,
        model=s.agent_model,
        num_ctx=s.agent_num_ctx,
        temperature=s.agent_temperature,
        reasoning=False,  # qwen3: no <think> trace; keeps CPU runs bounded
        keep_alive="60m",
        num_predict=1024,
    )


def _detectors(names: list[str]) -> list[guard_mod.Detector]:
    s = settings()
    out: list[guard_mod.Detector] = []
    for name in names:
        if name == "scaledown":
            if s.scaledown_enabled:
                out.append(guard_mod.ScaledownDetector(telemetry.scaledown_client()))
        elif name == "local":
            out.append(guard_mod.LocalJudgeDetector(s.ollama_base_url, s.judge_model))
        elif name == "heuristic":
            out.append(guard_mod.HeuristicDetector())
        else:
            raise ValueError(f"unknown detector {name!r}")
    return out


def _transient_model_error(exc: Exception) -> bool:
    """Model-server failures worth retrying: the Ollama runner was OOM-killed or restarted,
    or the connection dropped. Recorded so retries are visible, never silent."""
    transient = isinstance(exc, httpx.TransportError) or (
        isinstance(exc, ollama.ResponseError)
        and ("unexpectedly stopped" in str(exc) or exc.status_code >= 500))
    if transient:
        telemetry.record("model_retry", ok=False, meta={"error": repr(exc)[:300]})
        telemetry.emit("model_retry", error=repr(exc)[:300])
    return transient


def build_agent(flags: ProfileFlags, alert: str, checkpointer: BaseCheckpointSaver):
    """Middleware order matters; first is outermost. Tool-side, the chain runs
    ScaleDown compression -> log fold -> tool, so ScaleDown sees folded output."""
    s = settings()
    _register_harness_profile()
    if (flags.summarizer == "scaledown" or flags.tool_compression or flags.extraction) \
            and not s.scaledown_enabled:
        raise RuntimeError("profile needs ScaleDown but SCALEDOWN_API_KEY is not set")

    model = agent_model()
    backend = StateBackend()
    local = local_summarizer(model, DEEPAGENTS_DEFAULT_SUMMARY_PROMPT)
    summarizer = (scaledown_summarizer(telemetry.scaledown_client(), fallback=local)
                  if flags.summarizer == "scaledown" else local)

    middleware: list[AgentMiddleware] = [
        # Replaces Deep Agents' default summarization in place (same class name), keeping
        # its history offload to the backend; only the summary writer changes.
        SummarizationMiddleware(
            model=model,
            backend=backend,
            trigger=("tokens", int(s.agent_num_ctx * s.summarize_at_fraction)),
            keep=("messages", s.summarize_keep_messages),
            # The default (4000) trims with strategy="last", start_on="human". An autonomous
            # agent has one human message (the alert) at the very start, so once history
            # passes 4000 tokens the trimmed window is empty and the "summary" becomes the
            # placeholder "Previous conversation was too long to summarize." No error, all
            # findings lost. Send everything: ScaleDown takes 1M tokens, and the local
            # summarizer only ever sees ~summarize_at_fraction of num_ctx.
            trim_tokens_to_summarize=None,
            summarizer=summarizer,
        ),
        ModelCallLimitMiddleware(run_limit=s.max_model_calls, exit_behavior="end"),
        ToolResultProbeMiddleware(),  # outer on the tool side: sees post-compression size
    ]
    if flags.extraction:
        middleware.append(ScaledownExtractionMiddleware(
            EXTRACTION_ENTITIES, context_chars=0, inject_into_prompt=True,
            client=telemetry.scaledown_client()))
    if flags.guard != "off":
        detectors = _detectors(flags.detectors)
        middleware.append(guard_mod.CircuitBreakerMiddleware(
            alert, detectors, mode="enforce" if flags.guard == "enforce" else "shadow",
            gate=flags.guard_gate))
    if flags.tool_compression:
        middleware.append(ScaledownToolCompressionMiddleware(
            tools=BULKY_TOOLS, min_result_chars=4000, client=telemetry.scaledown_client()))
    if flags.log_fold:
        middleware.append(LogFoldMiddleware())
    middleware.append(ModelProbeMiddleware())  # measures the final request, once per step
    # Innermost: a crashed model server costs a retry, not the run. Inside the probe so a
    # retried call is still one step; the checkpoint covers anything longer than this.
    middleware.append(ModelRetryMiddleware(
        max_retries=3, retry_on=_transient_model_error, on_failure="error",
        initial_delay=10.0, backoff_factor=2.0, max_delay=60.0))

    return create_deep_agent(
        model=model,
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPTS[flags.prompt],
        middleware=middleware,
        backend=backend,
        checkpointer=checkpointer,
        name="oncall-agent",
    )
