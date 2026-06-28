"""
Qwen3 reasoning helpers.

Qwen3 is a hybrid reasoning model. By default every reply is shaped like:

    <think>
    step-by-step internal reasoning ...
    </think>
    the actual answer

Two things follow from that, and this module handles both:

1. Anything downstream that parses the model output (JSON facts, a single
   number, a yes/no verdict) must strip the <think> block first, or it chokes
   on the reasoning trace.
2. The reasoning trace itself is valuable — it's *why* the agent decided what
   it did — so we keep it rather than throw it away. The Verifier and the
   provenance log can reference it.

`/no_think` is Qwen3's soft switch: appended to a prompt it tells the model to
skip the thinking block for that turn. We use it for the fact extractor where we
need a deterministic, parseable answer and don't care about the trace.
"""

import re
from dataclasses import dataclass

from ollama import Client

from config import MODEL, OLLAMA_BASE_URL, ReasoningConfig

_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)

client = Client(host=OLLAMA_BASE_URL)


@dataclass
class ReasonedReply:
    """A model reply split into its reasoning trace and its final answer."""
    answer: str          # the response with the <think> block removed
    reasoning: str       # the content of the <think> block ("" if none)
    raw: str             # the untouched model output


def split_thinking(text: str) -> ReasonedReply:
    """Separate a Qwen3 reply into reasoning trace and clean answer."""
    match = _THINK_RE.search(text)
    reasoning = match.group(1).strip() if match else ""
    answer = _THINK_RE.sub("", text).strip()
    return ReasonedReply(answer=answer, reasoning=reasoning, raw=text)


def chat(
    prompt: str,
    *,
    cfg: ReasoningConfig,
    model: str = MODEL,
    system: str | None = None,
) -> ReasonedReply:
    """
    Single-turn chat against the local reasoning model.

    When cfg.enable_thinking is False we append `/no_think`, so Qwen3 returns a
    direct answer with no <think> block — exactly what JSON-parsing callers want.
    """
    user_content = prompt if cfg.enable_thinking else f"{prompt}\n\n/no_think"

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_content})

    response = client.chat(
        model=model,
        messages=messages,
        options={"temperature": cfg.temperature},
    )
    return split_thinking(response["message"]["content"])
