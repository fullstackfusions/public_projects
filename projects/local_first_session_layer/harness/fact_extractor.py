"""
Fact extractor — the compression step at session close.

Takes the accumulated session context (~tens of thousands of tokens of
retrieval + reasoning + verification) and squeezes it down to 3–8 durable,
self-contained facts that are worth carrying into the next session.

Why this runs in /no_think mode: we need a clean JSON array back. Qwen3's
reasoning trace would sit in front of the JSON and break the parse, so the
extractor deliberately suppresses thinking (config.EXTRACTOR_REASONING). The
*Reasoner* agent is where Qwen3 gets to think; the extractor just formats.
"""

import json

from config import EXTRACTOR_REASONING
from harness.reasoning import chat

EXTRACTION_PROMPT = """\
You are extracting durable facts from an agent session for long-term memory storage.

Rules:
- Extract 3-8 facts maximum
- Each fact must be self-contained — understandable without the session context
- Include specific values (percentages, dates, clause numbers) when present
- Exclude reasoning steps, tool call details, and procedural actions
- Confidence: "high" if verified by harness, "medium" if retrieved only

Session content:
{session_content}

Return ONLY a JSON array, no other text:
[
  {{
    "fact": "...",
    "confidence": "high|medium",
    "source_type": "retrieved|verified|decided",
    "guideline_ref": "optional — e.g. OSFI-B20-v3.2 clause 4.1"
  }}
]
"""


def _coerce_json_array(raw: str) -> list[dict]:
    """Best-effort recovery of a JSON array from a model reply."""
    raw = raw.strip()

    # Strip markdown fences if the model added them.
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fall back to the outermost [...] span — guards against a stray
        # leading/trailing token the model occasionally emits.
        start, end = raw.find("["), raw.rfind("]")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def extract_facts(session_content: str) -> list[dict]:
    """Compress a session transcript into a list of fact dicts."""
    reply = chat(
        EXTRACTION_PROMPT.format(session_content=session_content),
        cfg=EXTRACTOR_REASONING,  # /no_think → clean JSON, no reasoning trace
    )
    return _coerce_json_array(reply.answer)
