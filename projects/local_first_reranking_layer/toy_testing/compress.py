"""
SmartCrusher compression of the surviving chunks (the Part 3 carry-over).

Reranking decides WHICH chunks reach the model; SmartCrusher squeezes the ones
that do. The two layers compose: Part 4 (retrieval quality) sits upstream of
Part 3 (content compression). Here we run Headroom's deterministic rule-based
path (SmartCrusher for JSON, plus its prose handling) over the kept chunks,
and report tokens before/after so the table can separate the reranking win
(fewer chunks) from the compression win (smaller chunks).
"""

from __future__ import annotations

import tiktoken

from projects.local_first_reranking_layer.config import SMARTCRUSHER_ENABLED
from projects.local_first_reranking_layer.retrieval import Candidate

_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def _candidates_to_messages(candidates: list[Candidate]) -> list[dict]:
    """
    Wrap each kept chunk as a tool_result block so Headroom's router can dispatch
    JSON chunks to SmartCrusher and prose chunks to its prose path — the same
    wire shape Part 3 used.
    """
    blocks = []
    for i, c in enumerate(candidates):
        blocks.append({
            "type": "tool_result",
            "tool_use_id": f"chunk_{i:02d}",
            "content": c.doc.text,
        })
    return [{"role": "user", "content": blocks}]


def compress_chunks(candidates: list[Candidate]) -> dict:
    """
    Returns:
      texts          — the (possibly compressed) chunk texts to hand to the model
      tokens_before  — tiktoken tokens of the raw kept chunks
      tokens_after   — tokens actually sent
      transforms     — Headroom transforms applied (empty when disabled/failed)
    """
    raw_texts = [c.doc.text for c in candidates]
    tokens_before = sum(count_tokens(t) for t in raw_texts)

    if not SMARTCRUSHER_ENABLED:
        return {"texts": raw_texts, "tokens_before": tokens_before,
                "tokens_after": tokens_before, "transforms": []}

    try:
        from headroom import compress as hd_compress
        messages = _candidates_to_messages(candidates)
        result = hd_compress(
            messages,
            model="gpt-4o",
            compress_user_messages=True,
            protect_recent=0,
            kompress_model="disabled",     # rule-based only (SmartCrusher), deterministic
        )
        # Pull compressed text back out of the returned tool_result blocks.
        texts: list[str] = []
        for msg in result.messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "tool_result":
                        inner = block.get("content", "")
                        texts.append(inner if isinstance(inner, str) else str(inner))
        if not texts:                      # defensive: fall back to raw
            texts = raw_texts
        return {
            "texts": texts,
            "tokens_before": result.tokens_before,
            "tokens_after": result.tokens_after,
            "transforms": list(result.transforms_applied or []),
        }
    except Exception as exc:
        print(f"[smartcrusher] compress() failed ({exc}); sending raw chunks")
        return {"texts": raw_texts, "tokens_before": tokens_before,
                "tokens_after": tokens_before, "transforms": []}
