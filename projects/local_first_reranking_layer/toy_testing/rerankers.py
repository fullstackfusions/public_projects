"""
The reranking stage — the variable Part 4 measures.

A reranker takes the first stage's top-N candidates and re-orders them with a
cross-encoder that reads (query, document) jointly. It then keeps only the
top-k. This is what lets far fewer, far more relevant tokens reach the model.

Four implementations behind one interface:

  none       — passthrough. Keeps the bi-encoder's order. This is Config A,
               the "no reranker" baseline that shows what over-fetching costs.
  flashrank  — tiny ONNX cross-encoder, pure CPU, deterministic, weights local.
  bge        — neural cross-encoder (bge-reranker-v2-m3), CPU, Apache-2.0,
               weights local. Cohere-class quality with nothing leaving the box.
  cohere     — hosted API. Off-premises. Only available if COHERE_API_KEY is set;
               included purely as the data-residency contrast.

All local rerankers download weights once, then run fully offline.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from projects.local_first_reranking_layer.config import (
    FLASHRANK_MODEL, BGE_MODEL, COHERE_MODEL, COHERE_API_KEY, FINAL_TOP_K,
)
from projects.local_first_reranking_layer.retrieval import Candidate


@dataclass
class RerankResult:
    kept: list[Candidate]        # top-k, in reranked order (score = reranker score)
    latency_s: float             # wall time of the rerank() call only
    local: bool                  # True if nothing left the machine


class BaseReranker:
    name = "base"
    local = True

    def rerank(self, query: str, candidates: list[Candidate], top_k: int = FINAL_TOP_K) -> RerankResult:
        raise NotImplementedError


class NoReranker(BaseReranker):
    """Config A: keep the first stage's order. The over-fetch, unfixed."""
    name = "none"

    def rerank(self, query, candidates, top_k=FINAL_TOP_K):
        t0 = time.perf_counter()
        kept = candidates[:top_k]
        return RerankResult(kept, time.perf_counter() - t0, local=True)


class FlashRankReranker(BaseReranker):
    """Tiny ONNX cross-encoder. Pure CPU, deterministic, ~1ms/pair once warm."""
    name = "flashrank"

    def __init__(self, model_name: str = FLASHRANK_MODEL):
        from flashrank import Ranker
        # Downloads + loads the ONNX model. First construction is the cold start.
        self.ranker = Ranker(model_name=model_name)

    def rerank(self, query, candidates, top_k=FINAL_TOP_K):
        from flashrank import RerankRequest
        passages = [{"id": i, "text": c.doc.text} for i, c in enumerate(candidates)]
        t0 = time.perf_counter()
        ranked = self.ranker.rerank(RerankRequest(query=query, passages=passages))
        latency = time.perf_counter() - t0
        kept = [
            Candidate(candidates[r["id"]].doc, float(r["score"]))
            for r in ranked[:top_k]
        ]
        return RerankResult(kept, latency, local=True)


class BGEReranker(BaseReranker):
    """Neural cross-encoder (bge-reranker-v2-m3). CPU, Apache-2.0, weights local."""
    name = "bge"

    def __init__(self, model_name: str = BGE_MODEL):
        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(model_name, device="cpu")

    def rerank(self, query, candidates, top_k=FINAL_TOP_K):
        pairs = [(query, c.doc.text) for c in candidates]
        t0 = time.perf_counter()
        scores = self.model.predict(pairs, show_progress_bar=False)
        latency = time.perf_counter() - t0
        order = sorted(range(len(candidates)), key=lambda i: float(scores[i]), reverse=True)
        kept = [Candidate(candidates[i].doc, float(scores[i])) for i in order[:top_k]]
        return RerankResult(kept, latency, local=True)


class CohereReranker(BaseReranker):
    """Hosted API. Off-premises — every candidate leaves the machine. Opt-in only."""
    name = "cohere"
    local = False

    def __init__(self, model_name: str = COHERE_MODEL, api_key: str | None = COHERE_API_KEY):
        if not api_key:
            raise RuntimeError("COHERE_API_KEY is not set; Cohere reranker unavailable.")
        import cohere
        self.client = cohere.Client(api_key)
        self.model_name = model_name

    def rerank(self, query, candidates, top_k=FINAL_TOP_K):
        docs = [c.doc.text for c in candidates]
        t0 = time.perf_counter()
        resp = self.client.rerank(
            model=self.model_name, query=query, documents=docs, top_n=top_k
        )
        latency = time.perf_counter() - t0
        kept = [
            Candidate(candidates[r.index].doc, float(r.relevance_score))
            for r in resp.results
        ]
        return RerankResult(kept, latency, local=False)


_REGISTRY = {
    "none": NoReranker,
    "flashrank": FlashRankReranker,
    "bge": BGEReranker,
    "cohere": CohereReranker,
}


def get_reranker(name: str) -> BaseReranker:
    if name not in _REGISTRY:
        raise ValueError(f"Unknown reranker '{name}'. Options: {list(_REGISTRY)}")
    return _REGISTRY[name]()
