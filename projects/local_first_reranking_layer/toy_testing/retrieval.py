"""
First-stage retrieval: a CPU bi-encoder over the whole corpus.

This is the stage that over-fetches. A bi-encoder embeds the query and every
document independently, then ranks by cosine similarity. It has no cross-
attention between query and document, so for a query like "transaction record
retention" it cannot tell the gold "7 years" chunk apart from forty other
retention chunks — it pulls a pile of near-duplicates into the top-N.

That pile is the answer to Part 4's question: the tokens arrived because the
cheap first stage could not order them. The reranker (rerankers.py) is the fix.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from projects.local_first_reranking_layer.config import EMBED_MODEL, FIRST_STAGE_TOP_N
from projects.local_first_reranking_layer.data.corpus import Doc


@dataclass
class Candidate:
    doc: Doc
    score: float          # first-stage cosine similarity


class BiEncoderRetriever:
    """Embeds the corpus once, then serves top-N candidates per query. CPU-only."""

    def __init__(self, corpus: list[Doc], model_name: str = EMBED_MODEL):
        from sentence_transformers import SentenceTransformer

        self.corpus = corpus
        self.model = SentenceTransformer(model_name, device="cpu")
        t0 = time.perf_counter()
        self._embeddings = self.model.encode(
            [d.text for d in corpus],
            batch_size=64,
            convert_to_numpy=True,
            normalize_embeddings=True,   # cosine == dot product on normalized vectors
            show_progress_bar=False,
        )
        self.index_build_s = round(time.perf_counter() - t0, 2)

    def retrieve(self, query: str, top_n: int = FIRST_STAGE_TOP_N) -> tuple[list[Candidate], float]:
        """Return (top-N candidates, retrieval_latency_seconds)."""
        t0 = time.perf_counter()
        q = self.model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
        )[0]
        scores = self._embeddings @ q                    # cosine similarity
        top_idx = np.argsort(-scores)[:top_n]
        elapsed = time.perf_counter() - t0
        candidates = [Candidate(self.corpus[i], float(scores[i])) for i in top_idx]
        return candidates, elapsed
