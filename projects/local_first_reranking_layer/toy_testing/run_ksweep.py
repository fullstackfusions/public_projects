"""
[measure] cell #2 — the k-sweep table.

Fix the reranker (the best local one, bge, by default) and tighten the number
of chunks kept: top-10 → top-5 → top-3 → top-1. The question this answers is
the inverse of Config A: with a reranker you can TRUST, how few tokens can you
let arrive before correctness breaks?

This is the direct payoff for the series arc. Part 3 compressed whatever showed
up; Part 4 shows that a good reranker lets you keep top-3 (or even top-1) and
hold answer quality — so most of those tokens never needed to arrive at all.

Usage:
  python -m projects.local_first_reranking_layer.run_ksweep
  python -m projects.local_first_reranking_layer.run_ksweep --reranker flashrank --save
"""

from __future__ import annotations

import argparse
import statistics as stats

from projects.local_first_reranking_layer._quiet import quiet
from projects.local_first_reranking_layer.config import (
    MODEL, FIRST_STAGE_TOP_N, N_DISTRACTORS, CORPUS_SEED,
)
from projects.local_first_reranking_layer.data.corpus import build_corpus, EVAL_QUERIES
from projects.local_first_reranking_layer.retrieval import BiEncoderRetriever
from projects.local_first_reranking_layer.rerankers import get_reranker
from projects.local_first_reranking_layer.graph import Pipeline
from projects.local_first_reranking_layer.scoring import is_correct, gold_hit
from projects.local_first_reranking_layer.report import print_table, save_results

K_VALUES = [10, 5, 3, 1]


def _mean(xs):
    return round(stats.mean(xs), 1) if xs else 0.0


def sweep_k(pipe: Pipeline, top_k: int, generate: bool) -> dict:
    correct = gold_hits = 0
    chunk_tokens, prompt_tokens = [], []
    for q in EVAL_QUERIES:
        state = pipe.run(q.question, top_n=FIRST_STAGE_TOP_N, top_k=top_k, generate=generate)
        gold_hits += int(gold_hit(q, state["kept"]))
        chunk_tokens.append(state["tokens_chunks_sent"])
        if generate:
            correct += int(is_correct(q, state["answer"]))
            prompt_tokens.append(state["prompt_tokens"])
    n = len(EVAL_QUERIES)
    return {
        "top_k": top_k,
        "gold_hit": f"{gold_hits}/{n}",
        "correct": f"{correct}/{n}" if generate else "—",
        "avg_chunk_tokens": int(_mean(chunk_tokens)),
        "avg_prompt_tokens": int(_mean(prompt_tokens)) if generate else "—",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reranker", default="bge", choices=["none", "flashrank", "bge", "cohere"],
                    help="reranker to hold fixed across the sweep (default: bge)")
    ap.add_argument("--no-generate", action="store_true")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    quiet()
    generate = not args.no_generate

    corpus = build_corpus(n_distractors=N_DISTRACTORS, seed=CORPUS_SEED)
    print(f"Embedding corpus (CPU) …  reranker={args.reranker}  model={MODEL}")
    retriever = BiEncoderRetriever(corpus)
    pipe = Pipeline(retriever, get_reranker(args.reranker))

    rows_data = []
    for k in K_VALUES:
        print(f"\n── top_k = {k} " + "─" * 30)
        rows_data.append(sweep_k(pipe, k, generate))

    headers = ["top_k", "gold-hit@k", "correct", "chunk tok", "prompt tok"]
    rows = [[r["top_k"], r["gold_hit"], r["correct"],
             r["avg_chunk_tokens"], r["avg_prompt_tokens"]] for r in rows_data]
    print()
    print_table(
        f"k-sweep  |  reranker={args.reranker}  |  {MODEL}", headers, rows,
        caption="As k tightens, watch how long correctness holds. The gap "
                "between gold-hit and correct is the model; gold-hit falling is the reranker.")

    if args.save:
        save_results("results_ksweep.json",
                     {"model": MODEL, "reranker": args.reranker, "sweep": rows_data})


if __name__ == "__main__":
    main()
