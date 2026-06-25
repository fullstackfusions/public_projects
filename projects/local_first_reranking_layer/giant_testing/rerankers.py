"""
Reranker implementations — the variable under test.

Same four options as the toy experiment (none / flashrank / bge / cohere),
now applied to real document chunks. The cross-encoder reads (query, chunk)
jointly; at this scale the quality gap between bi-encoder order and
cross-encoder order is far more pronounced because the corpus has many
lexically-similar chunks talking about the same concept across different
chapters and sections.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from projects.local_first_reranking_layer.giant_testing.config import (
    FLASHRANK_MODEL, BGE_MODEL, COHERE_MODEL, COHERE_API_KEY, FINAL_TOP_K,
)
from projects.local_first_reranking_layer.giant_testing.retrieval import Candidate


@dataclass
class RerankResult:
    kept: list[Candidate]
    latency_s: float
    local: bool


class NoReranker:
    name = "none"
    local = True

    def rerank(self, query: str, candidates: list[Candidate],
               top_k: int = FINAL_TOP_K) -> RerankResult:
        t0 = time.perf_counter()
        return RerankResult(candidates[:top_k], time.perf_counter() - t0, local=True)


class FlashRankReranker:
    name = "flashrank"
    local = True

    def __init__(self, model_name: str = FLASHRANK_MODEL):
        from flashrank import Ranker
        self.ranker = Ranker(model_name=model_name)

    def rerank(self, query: str, candidates: list[Candidate],
               top_k: int = FINAL_TOP_K) -> RerankResult:
        from flashrank import RerankRequest
        passages = [{"id": i, "text": c.chunk.text} for i, c in enumerate(candidates)]
        t0 = time.perf_counter()
        ranked = self.ranker.rerank(RerankRequest(query=query, passages=passages))
        latency = time.perf_counter() - t0
        kept = [
            Candidate(candidates[r["id"]].chunk, float(r["score"]))
            for r in ranked[:top_k]
        ]
        return RerankResult(kept, latency, local=True)


class BGEReranker:
    name = "bge"
    local = True

    def __init__(self, model_name: str = BGE_MODEL):
        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(model_name, device="cpu")

    def rerank(self, query: str, candidates: list[Candidate],
               top_k: int = FINAL_TOP_K) -> RerankResult:
        pairs = [(query, c.chunk.text) for c in candidates]
        t0 = time.perf_counter()
        scores = self.model.predict(pairs, show_progress_bar=False)
        latency = time.perf_counter() - t0
        order = sorted(range(len(candidates)), key=lambda i: float(scores[i]), reverse=True)
        kept = [Candidate(candidates[i].chunk, float(scores[i])) for i in order[:top_k]]
        return RerankResult(kept, latency, local=True)


class CohereReranker:
    name = "cohere"
    local = False

    def __init__(self, model_name: str = COHERE_MODEL, api_key: str | None = COHERE_API_KEY):
        if not api_key:
            raise RuntimeError("COHERE_API_KEY not set.")
        import cohere
        self.client = cohere.Client(api_key)
        self.model_name = model_name

    def rerank(self, query: str, candidates: list[Candidate],
               top_k: int = FINAL_TOP_K) -> RerankResult:
        docs = [c.chunk.text for c in candidates]
        t0 = time.perf_counter()
        resp = self.client.rerank(
            model=self.model_name, query=query, documents=docs, top_n=top_k)
        latency = time.perf_counter() - t0
        kept = [
            Candidate(candidates[r.index].chunk, float(r.relevance_score))
            for r in resp.results
        ]
        return RerankResult(kept, latency, local=False)


_REGISTRY = {
    "none": NoReranker,
    "flashrank": FlashRankReranker,
    "bge": BGEReranker,
    "cohere": CohereReranker,
}


def get_reranker(name: str):
    if name not in _REGISTRY:
        raise ValueError(f"Unknown reranker '{name}'. Options: {list(_REGISTRY)}")
    return _REGISTRY[name]()
