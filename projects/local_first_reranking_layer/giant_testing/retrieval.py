"""
First-stage retrieval: loads the persisted index and searches with a CPU bi-encoder.

At real scale (~1,030 chunks across two documents), the bi-encoder still runs in
milliseconds per query — that hasn't changed.  What changes is the QUALITY of the
top-N: with hundreds of chunks on the same topic (e.g., every ML chapter mentioning
"Sharpe ratio", every law chapter discussing "data protection") the bi-encoder
drags far more irrelevant candidates into the top-N than it did with the toy
corpus.  That degradation is what the reranker (rerankers.py) is here to fix.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

import numpy as np

from projects.local_first_reranking_layer.giant_testing.config import (
    CHUNKS_FILE, EMBEDDINGS_FILE, EMBED_MODEL, FIRST_STAGE_TOP_N,
)


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    page_start: int
    page_end: int
    chunk_idx: int


@dataclass
class Candidate:
    chunk: Chunk
    score: float      # cosine similarity from bi-encoder


def _load_index() -> tuple[list[Chunk], np.ndarray]:
    if not CHUNKS_FILE.exists() or not EMBEDDINGS_FILE.exists():
        raise FileNotFoundError(
            "Index not found. Run ingest.py first:\n"
            "  python -m projects.local_first_reranking_layer.giant_testing.ingest"
        )
    raw = json.loads(CHUNKS_FILE.read_text())
    chunks = [Chunk(**r) for r in raw]
    embeddings = np.load(str(EMBEDDINGS_FILE))
    return chunks, embeddings


class BiEncoderRetriever:
    """
    Loads the persisted index once and serves top-N candidates per query.
    Construct at process startup; the corpus is already embedded.
    """

    def __init__(self, model_name: str = EMBED_MODEL):
        from sentence_transformers import SentenceTransformer
        self.chunks, self.embeddings = _load_index()
        self.model = SentenceTransformer(model_name, device="cpu")
        print(f"[retrieval_agent] index loaded: {len(self.chunks)} chunks "
              f"from {len(set(c.source for c in self.chunks))} sources")

    def retrieve(self, query: str, top_n: int = FIRST_STAGE_TOP_N) -> tuple[list[Candidate], float]:
        """Return (top-N candidates ordered by cosine score, latency_seconds)."""
        t0 = time.perf_counter()
        q_vec = self.model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True,
            show_progress_bar=False
        )[0]
        scores = self.embeddings @ q_vec
        top_idx = np.argsort(-scores)[:top_n]
        elapsed = time.perf_counter() - t0
        candidates = [Candidate(self.chunks[i], float(scores[i])) for i in top_idx]
        return candidates, elapsed

    @property
    def total_tokens(self) -> int:
        """Tiktoken estimate of the entire corpus — the 'stuff everything' upper bound."""
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return sum(len(enc.encode(c.text)) for c in self.chunks)
