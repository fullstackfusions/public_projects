"""
[measure] cell #3 — FlashRank cold-start vs warm latency.

The well-established FlashRank behavior: the first time you touch the reranker it
pays a one-time cost to load the ONNX model into memory; after that, inference is
cheap and stable. This script confirms it on your hardware — and, importantly,
times cold vs warm inference on the SAME candidate set, so the comparison
reflects warmth and not differing text lengths.

Three things are reported:
  • model construction  — the one-time load (this is the real cold cost)
  • first user request   — construction + first inference, i.e. what a lazily-
                           initialised reranker makes the first request pay
  • warm inference       — steady-state per-call cost once constructed

Operational takeaway: construct the reranker at process startup, not on the
first user request, so no single request eats the load.

Usage:
  python -m projects.local_first_reranking_layer.bench_coldstart
  python -m projects.local_first_reranking_layer.bench_coldstart --warm-runs 50
"""

from __future__ import annotations

import argparse
import statistics as stats
import time

from projects.local_first_reranking_layer._quiet import quiet
from projects.local_first_reranking_layer.config import (
    FLASHRANK_MODEL, FIRST_STAGE_TOP_N, N_DISTRACTORS, CORPUS_SEED,
)
from projects.local_first_reranking_layer.data.corpus import build_corpus, EVAL_QUERIES
from projects.local_first_reranking_layer.retrieval import BiEncoderRetriever
from projects.local_first_reranking_layer.report import print_table


def main():
    quiet()
    ap = argparse.ArgumentParser()
    ap.add_argument("--warm-runs", type=int, default=30)
    args = ap.parse_args()

    corpus = build_corpus(n_distractors=N_DISTRACTORS, seed=CORPUS_SEED)
    print("Embedding corpus to produce a realistic candidate set (CPU) …")
    retriever = BiEncoderRetriever(corpus)

    # Hold ONE candidate set fixed for the whole timing run, so cold-vs-warm
    # reflects model warmth and not differing passage lengths.
    fixed_query = EVAL_QUERIES[0].question
    fixed_candidates = retriever.retrieve(fixed_query, top_n=FIRST_STAGE_TOP_N)[0]
    n_pairs = len(fixed_candidates)

    from flashrank import Ranker, RerankRequest

    # 1) model construction — the one-time cold cost.
    t0 = time.perf_counter()
    ranker = Ranker(model_name=FLASHRANK_MODEL)
    construct_ms = (time.perf_counter() - t0) * 1000

    passages = [{"id": i, "c": c} for i, c in enumerate(fixed_candidates)]

    def _rerank() -> float:
        req = RerankRequest(query=fixed_query,
                            passages=[{"id": p["id"], "text": p["c"].doc.text} for p in passages])
        t = time.perf_counter()
        ranker.rerank(req)
        return (time.perf_counter() - t) * 1000

    # 2) inference, same set every time: first call (cold) then warm steady-state.
    samples = [_rerank() for _ in range(args.warm_runs + 1)]
    cold_inf = samples[0]
    warm = samples[1:]
    warm_p50 = stats.median(warm)

    rows = [
        ["model construction", round(construct_ms, 1), "—", "one-time load of ONNX into memory"],
        ["first user request (lazy init)", round(construct_ms + cold_inf, 1),
         round((construct_ms + cold_inf) / n_pairs, 3), "construction + first inference"],
        ["first inference (cold)", round(cold_inf, 1), round(cold_inf / n_pairs, 3),
         f"{n_pairs} pairs, graph not yet warm"],
        [f"warm inference (median of {len(warm)})", round(warm_p50, 1),
         round(warm_p50 / n_pairs, 3), f"{n_pairs} pairs/call, steady state"],
    ]
    print()
    print_table(
        f"FlashRank cold-start  |  {FLASHRANK_MODEL}",
        ["phase", "total ms", "ms / pair", "note"], rows,
        caption="The one-time cost is construction. Build the reranker at startup, "
                "not on the first user request.")


if __name__ == "__main__":
    main()
