"""
SmartCrusher compression of the surviving reranked chunks.

At real PDF scale the chunks are genuine prose (book chapters, legal sections),
so SmartCrusher's JSON/code paths rarely fire — it mostly no-ops or lightly
trims redundant whitespace.  That is the honest finding: reranking (which chunks)
dominates the token story; compression (how big each chunk is) is a secondary
gain.  We still run it so the comparison is faithful to the full Part 3 + 4 stack.
"""

from __future__ import annotations

import tiktoken

from projects.local_first_reranking_layer.giant_testing.config import SMARTCRUSHER_ENABLED
from projects.local_first_reranking_layer.giant_testing.retrieval import Candidate

_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_enc.encode(text, disallowed_special=()))


def compress_chunks(candidates: list[Candidate]) -> dict:
    """
    Returns:
      texts          — compressed (or raw) chunk texts to hand to the model
      tokens_before  — tiktoken count before SmartCrusher
      tokens_after   — tokens actually sent
      transforms     — Headroom transforms applied
    """
    raw_texts = [c.chunk.text for c in candidates]
    tokens_before = sum(count_tokens(t) for t in raw_texts)

    if not SMARTCRUSHER_ENABLED:
        return {"texts": raw_texts, "tokens_before": tokens_before,
                "tokens_after": tokens_before, "transforms": []}

    try:
        from headroom import compress as hd_compress
        messages = [{"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": f"chunk_{i:03d}", "content": t}
            for i, t in enumerate(raw_texts)
        ]}]
        result = hd_compress(
            messages, model="gpt-4o",
            compress_user_messages=True, protect_recent=0, kompress_model="disabled",
        )
        texts: list[str] = []
        for msg in result.messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "tool_result":
                        inner = block.get("content", "")
                        texts.append(inner if isinstance(inner, str) else str(inner))
        if not texts:
            texts = raw_texts
        return {
            "texts": texts,
            "tokens_before": result.tokens_before,
            "tokens_after": result.tokens_after,
            "transforms": list(result.transforms_applied or []),
        }
    except Exception as exc:
        print(f"[compress_agent] SmartCrusher failed ({exc}); sending raw chunks")
        return {"texts": raw_texts, "tokens_before": tokens_before,
                "tokens_after": tokens_before, "transforms": []}
