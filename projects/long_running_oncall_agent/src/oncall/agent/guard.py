"""Circuit breaker for runaway agents: detect looping/drifting, nudge, then stop.

Design choices worth calling out:

- Runs in `before_model`, not `after_model`. Here the trajectory includes the latest
  tool result, and an injected nudge lands after the ToolMessages instead of between
  an AI tool call and its result (which breaks the tool-calling protocol).
- Detectors share one interface, so the same trajectory can be scored by several
  of them in *shadow* mode (record only) while one *enforces*.
- Guard state (nudges sent) lives in graph state, so it survives a worker crash and
  checkpoint resume instead of resetting.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Literal, NotRequired, Protocol

from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_ollama import ChatOllama
from langchain_scaledown import ScaledownAPIError, ScaledownClient

from oncall import telemetry

LABELS = ("progressing", "looping", "drifting")
CRITERIA = {
    "progressing": "The agent's recent steps investigate the incident described in the alert, "
                   "and each step returns new, relevant information that moves toward a root "
                   "cause.",
    "looping": "The agent keeps repeating the same or nearly identical tool call and gets the "
               "same result or error back, without changing its approach.",
    "drifting": "The agent's recent steps investigate services, warnings or problems that are "
                "unrelated to the incident described in the alert.",
}


@dataclass
class Verdict:
    detector: str
    label: str
    probs: dict[str, float]
    reason: str | None
    latency_ms: float
    ok: bool = True

    @property
    def non_progress(self) -> float:
        return max(self.probs.get("looping", 0.0), self.probs.get("drifting", 0.0))


class Detector(Protocol):
    name: str

    def classify(self, digest: str, steps: list[dict[str, Any]]) -> Verdict: ...


# --- Trajectory digest ---------------------------------------------------------------


def trajectory(messages: list) -> list[dict[str, Any]]:
    """Pair each tool call with its result, in order."""
    results = {m.tool_call_id: m for m in messages if isinstance(m, ToolMessage)}
    steps = []
    for m in messages:
        if isinstance(m, AIMessage):
            for call in m.tool_calls:
                res = results.get(call["id"])
                steps.append({"tool": call["name"],
                              "args": {k: v for k, v in call["args"].items()
                                       if k != "compression_query"},
                              "result": res.text if res else ""})
    return steps


def digest(alert: str, steps: list[dict[str, Any]], window: int = 12) -> str:
    lines = ["INCIDENT ALERT:", alert.strip(), "", "AGENT TRAJECTORY (most recent last):"]
    offset = max(0, len(steps) - window)
    for i, s in enumerate(steps[offset:], start=offset + 1):
        args = ", ".join(f"{k}={v}" for k, v in s["args"].items())
        result = " ".join(s["result"].split())[:220]
        lines.append(f"step {i}: {s['tool']}({args}) -> {result}")
    return "\n".join(lines)


# --- Detectors -----------------------------------------------------------------------


class HeuristicDetector:
    """Zero-cost baseline: repeated identical calls and error streaks. Cannot see drift."""

    name = "heuristic"

    def classify(self, digest: str, steps: list[dict[str, Any]]) -> Verdict:
        t0 = time.perf_counter()
        recent = steps[-6:]
        fingerprints = Counter(json.dumps([s["tool"], s["args"]], sort_keys=True) for s in recent)
        repeats = max(fingerprints.values(), default=0)
        streak = 0
        for s in reversed(steps):
            if s["result"].startswith(("HTTP 5", "request to")):
                streak += 1
            else:
                break
        loop = min(1.0, max((repeats - 1) / 3, (streak - 1) / 3, 0.0))
        verdict = Verdict(self.name, "looping" if loop >= 0.5 else "progressing",
                          {"progressing": 1 - loop, "looping": loop, "drifting": 0.0},
                          f"max identical calls in last 6={repeats}, error streak={streak}",
                          (time.perf_counter() - t0) * 1000)
        telemetry.record("heuristic_judge", latency_ms=verdict.latency_ms,
                         meta={"label": verdict.label, "probs": verdict.probs})
        return verdict


class ScaledownDetector:
    """ScaleDown Decisions API (`classify-1`) choice question over the digest."""

    name = "scaledown"

    def __init__(self, client: ScaledownClient) -> None:
        self.client = client

    def classify(self, digest: str, steps: list[dict[str, Any]]) -> Verdict:
        t0 = time.perf_counter()
        question = {"type": "choice", "criteria": CRITERIA,
                    "instructions": "Judge only the agent's recent behaviour against the alert."}
        try:
            answer = self.client.classify(digest, {"trajectory": question})["answers"]["trajectory"]
        except (ScaledownAPIError, KeyError, TypeError) as e:
            return Verdict(self.name, "unknown", {}, f"error: {e}"[:200],
                           (time.perf_counter() - t0) * 1000, ok=False)
        return Verdict(self.name, answer["choice"],
                       {k: float(v) for k, v in answer.get("probabilities", {}).items()},
                       answer.get("reasoning"), (time.perf_counter() - t0) * 1000)


_JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": list(LABELS)},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string"},
    },
    "required": ["label", "confidence", "reason"],
}


class LocalJudgeDetector:
    """A small local model with Ollama structured outputs: constrained decoding, on CPU."""

    def __init__(self, base_url: str, model: str) -> None:
        self.name = f"local:{model}"
        self.llm = ChatOllama(base_url=base_url, model=model, temperature=0, reasoning=False,
                              format=_JUDGE_SCHEMA, num_ctx=8192, num_predict=200)

    def classify(self, digest: str, steps: list[dict[str, Any]]) -> Verdict:
        prompt = ("Classify the agent's recent behaviour. Labels:\n"
                  + "\n".join(f"- {k}: {v}" for k, v in CRITERIA.items())
                  + f"\n\n{digest}\n\nAnswer as JSON.")
        t0 = time.perf_counter()
        try:
            ai = self.llm.invoke(prompt)
            out = json.loads(ai.text)
            label, conf = out["label"], float(out["confidence"])
        except Exception as e:  # noqa: BLE001 - any judge failure must not kill the run
            return Verdict(self.name, "unknown", {}, f"error: {e}"[:200],
                           (time.perf_counter() - t0) * 1000, ok=False)
        rest = (1 - conf) / (len(LABELS) - 1)
        verdict = Verdict(self.name, label, {k: conf if k == label else rest for k in LABELS},
                          out.get("reason"), (time.perf_counter() - t0) * 1000)
        telemetry.record("local_judge", in_tokens=telemetry.count_tokens(prompt),
                         out_tokens=telemetry.count_tokens(ai.text),
                         latency_ms=verdict.latency_ms,
                         meta={"model": self.llm.model, "label": label, "probs": verdict.probs})
        return verdict


# --- Middleware ------------------------------------------------------------------------


class GuardState(AgentState):
    guard: NotRequired[dict[str, Any]]


NUDGE = ("[circuit breaker] Your recent steps look like {label} (p={p:.2f}): {reason} "
         "Change approach: use a different tool or data source, re-read the alert, and focus on "
         "the affected service and its dependencies. If you already have enough evidence, "
         "submit the incident report now.")


class CircuitBreakerMiddleware(AgentMiddleware):
    """Score the trajectory before each model call; nudge at `soft`, stop at `hard`.

    Args:
        detectors: The first one enforces; the rest run in shadow mode for comparison.
        mode: "shadow" records verdicts only; "enforce" may nudge and stop.
        min_steps: Don't judge before this many tool calls.
        gate: If set, the paid/slow enforcing detector only runs when the free heuristic's
            non-progress score is at least this, or every `check_every` steps.
    """

    state_schema = GuardState  # type: ignore[assignment]

    def __init__(
        self,
        alert: str,
        detectors: list[Detector],
        *,
        mode: Literal["shadow", "enforce"] = "enforce",
        soft: float = 0.6,
        hard: float = 0.85,
        min_steps: int = 3,
        max_nudges: int = 1,
        gate: float | None = None,
        check_every: int = 3,
    ) -> None:
        super().__init__()
        self.alert = alert
        self.detectors = detectors
        self.mode = mode
        self.soft, self.hard = soft, hard
        self.min_steps = min_steps
        self.max_nudges = max_nudges
        self.gate = gate
        self.check_every = check_every
        self.heuristic = HeuristicDetector()

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: GuardState, runtime) -> dict[str, Any] | None:
        steps = trajectory(state["messages"])
        if len(steps) < self.min_steps:
            return None
        guard = dict(state.get("guard") or {"nudges": 0, "checks": 0})
        d = digest(self.alert, steps)

        heuristic = self.heuristic.classify(d, steps)
        run_paid = (self.gate is None or heuristic.non_progress >= self.gate
                    or len(steps) % self.check_every == 0)
        verdicts = [heuristic]
        if run_paid:
            verdicts += [det.classify(d, steps) for det in self.detectors]
        guard["checks"] += 1

        primary = verdicts[1] if run_paid and self.detectors else heuristic
        telemetry.emit("guard_check", tool_calls=len(steps), mode=self.mode,
                       primary=primary.detector, gated=not run_paid,
                       verdicts=[asdict(v) for v in verdicts])
        update: dict[str, Any] = {"guard": guard}
        if self.mode != "enforce" or not primary.ok:
            return update

        p = primary.non_progress
        if p >= self.hard and guard["nudges"] >= self.max_nudges:
            guard["stopped"] = asdict(primary)
            telemetry.emit("guard_stop", label=primary.label, p=p, reason=primary.reason)
            return {**update, "jump_to": "end", "messages": [AIMessage(
                content=f"Stopped by circuit breaker after {len(steps)} tool calls: agent is "
                        f"{primary.label} (p={p:.2f}, detector={primary.detector}). "
                        f"{primary.reason or ''}".strip())]}
        if p >= self.soft and guard["nudges"] < self.max_nudges:
            guard["nudges"] += 1
            telemetry.emit("guard_nudge", label=primary.label, p=p, reason=primary.reason)
            return {**update, "messages": [HumanMessage(content=NUDGE.format(
                label=primary.label, p=p, reason=primary.reason or ""))]}
        return update
