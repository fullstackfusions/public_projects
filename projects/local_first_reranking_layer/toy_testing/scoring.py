"""
Correctness and retrieval-quality scoring.

Two independent things are measured, and it matters that they're separate:

  • answer correctness  — did the model's final answer contain the gold fact?
    This is the end-to-end metric the A/B/C and k-sweep tables report.

  • gold-hit@k          — did the one correct chunk survive into the top-k that
    was actually sent to the model? This isolates the reranker from the LLM:
    a config can fail correctness because the reranker dropped the gold chunk
    (a retrieval failure) OR because the model fumbled it (a generation failure).
    Reporting both keeps the story honest.
"""

from __future__ import annotations

import re

from projects.local_first_reranking_layer.data.corpus import Query
from projects.local_first_reranking_layer.retrieval import Candidate

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def clean_answer(answer: str) -> str:
    """Strip qwen3 <think> traces before scoring so reasoning text can't match."""
    return _THINK_RE.sub("", answer or "").strip()


def is_correct(query: Query, answer: str) -> bool:
    text = clean_answer(answer).lower()
    return any(g.lower() in text for g in query.gold)


def gold_hit(query: Query, kept: list[Candidate]) -> bool:
    """True if the authoritative chunk for this query is in the kept set."""
    return any(c.doc.id == query.gold_doc_id for c in kept)


def gold_rank(query: Query, ordered: list[Candidate]) -> int | None:
    """1-based position of the gold chunk in an ordered list, or None if absent."""
    for i, c in enumerate(ordered):
        if c.doc.id == query.gold_doc_id:
            return i + 1
    return None
