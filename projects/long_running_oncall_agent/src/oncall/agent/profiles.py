"""Middleware profiles: named, frozen sets of flags. A run's resolved flags are stored
with the run, so a result can always be traced back to exactly what was enabled."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ProfileFlags(BaseModel):
    """Every knob that differs between profiles. Anything not here is held constant."""

    summarizer: Literal["local", "scaledown"] = "local"
    tool_compression: bool = False  # ScaledownToolCompressionMiddleware
    log_fold: bool = False  # deterministic fold of query_logs output
    extraction: bool = False  # ScaledownExtractionMiddleware on the alert
    guard: Literal["off", "shadow", "enforce"] = "shadow"
    # First detector enforces (in enforce mode); all are scored. Values:
    # "scaledown", "local" (judge_model via Ollama), "heuristic".
    detectors: list[str] = ["scaledown"]
    guard_gate: float | None = None  # see CircuitBreakerMiddleware.gate
    # "naive" drops the one prompt sentence that tells the agent not to retry failing tools.
    prompt: Literal["guarded", "naive"] = "guarded"


PROFILES: dict[str, ProfileFlags] = {
    # Deep Agents defaults (local summarization by the agent model), guard watching only.
    "baseline": ProfileFlags(),
    # Everything the blog describes, used as documented.
    "scaledown": ProfileFlags(summarizer="scaledown", tool_compression=True, extraction=True,
                              guard="enforce", detectors=["scaledown"]),
    # The blog's stack plus deterministic log folding in front of compression.
    "scaledown_fold": ProfileFlags(summarizer="scaledown", tool_compression=True, log_fold=True,
                                   extraction=True, guard="enforce", detectors=["scaledown"]),
    # Loop-trap experiment: same as baseline / scaledown, minus the "don't retry" sentence.
    "baseline_naive": ProfileFlags(prompt="naive"),
    "scaledown_naive": ProfileFlags(summarizer="scaledown", tool_compression=True,
                                    extraction=True, guard="enforce", detectors=["scaledown"],
                                    prompt="naive"),
    # Ablations: one change at a time against baseline.
    "fold_only": ProfileFlags(log_fold=True),
    "guard_scaledown": ProfileFlags(guard="enforce", detectors=["scaledown", "heuristic"]),
    "guard_local": ProfileFlags(guard="enforce", detectors=["local", "heuristic"]),
    "guard_heuristic": ProfileFlags(guard="enforce", detectors=["heuristic"]),
}


def resolve(profile: str, overrides: dict[str, Any] | None = None) -> ProfileFlags:
    if profile not in PROFILES:
        raise KeyError(f"unknown profile {profile!r}; have {sorted(PROFILES)}")
    return PROFILES[profile].model_copy(update=overrides or {})
