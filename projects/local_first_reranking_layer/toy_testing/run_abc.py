"""
[measure] cell #1 — the A/B/C(/D) config table.

Runs the SAME pipeline (retrieve → rerank → compress → generate) over the SAME
corpus and queries, changing ONLY the reranker, at a fixed top-k. That isolates
retrieval quality: every config sends roughly the same number of chunk tokens,
so differences in correctness come from WHICH chunks each reranker surfaced.

  Config A  none       — first-stage order (the over-fetch, unfixed)
  Config B  flashrank  — tiny CPU cross-encoder, deterministic
  Config C  bge        — neural CPU cross-encoder (bge-reranker-v2-m3)
  Config D  cohere     — off-premises API (only if COHERE_API_KEY is set)

It also prints the over-fetch anchor that motivates the whole post: how many
tokens the first stage's raw top-N would have dumped into the window versus how
few survive after reranking to top-k. That is "why did 3,496 tokens arrive?"

Usage:
  python -m projects.local_first_reranking_layer.run_abc
  python -m projects.local_first_reranking_layer.run_abc --top-k 5 --save
  python -m projects.local_first_reranking_layer.run_abc --no-generate   # fast, retrieval-only
"""

from __future__ import annotations

import argparse
import statistics as stats

from projects.local_first_reranking_layer._quiet import quiet
from projects.local_first_reranking_layer.config import (
    MODEL, RERANKERS, COHERE_API_KEY, FIRST_STAGE_TOP_N, FINAL_TOP_K, N_DISTRACTORS, CORPUS_SEED,
)
from projects.local_first_reranking_layer.data.corpus import build_corpus, corpus_stats, EVAL_QUERIES
from projects.local_first_reranking_layer.retrieval import BiEncoderRetriever
from projects.local_first_reranking_layer.rerankers import get_reranker
from projects.local_first_reranking_layer.graph import Pipeline
from projects.local_first_reranking_layer.compress import count_tokens
from projects.local_first_reranking_layer.scoring import is_correct, gold_hit, gold_rank
from projects.local_first_reranking_layer.report import print_table, save_results


def _mean(xs):
    return round(stats.mean(xs), 2) if xs else 0.0


def run_config(name: str, retriever: BiEncoderRetriever, top_n: int, top_k: int,
               generate: bool) -> dict:
    reranker = get_reranker(name)
    pipe = Pipeline(retriever, reranker)

    correct = gold_hits = 0
    chunk_tokens, prompt_tokens, completion_tokens = [], [], []
    rerank_ms, generate_s, gold_ranks = [], [], []

    print(f"\n── Config: {name}  (local={reranker.local}) " + "─" * 30)
    for q in EVAL_QUERIES:
        state = pipe.run(q.question, top_n=top_n, top_k=top_k, generate=generate)
        hit = gold_hit(q, state["kept"])
        gr = gold_rank(q, state["kept"])
        gold_hits += int(hit)
        chunk_tokens.append(state["tokens_chunks_sent"])
        rerank_ms.append(state["rerank_s"] * 1000)
        gold_ranks.append(gr if gr else top_k + 1)

        ok = "?"
        if generate:
            ok_bool = is_correct(q, state["answer"])
            correct += int(ok_bool)
            prompt_tokens.append(state["prompt_tokens"])
            completion_tokens.append(state["completion_tokens"])
            generate_s.append(state["generate_s"])
            ok = "✓" if ok_bool else "✗"
        print(f"   {q.id:<13} gold@{str(gr) if gr else '—':<3} "
              f"hit={'Y' if hit else 'N'} correct={ok}")

    n = len(EVAL_QUERIES)
    return {
        "reranker": name,
        "local": reranker.local,
        "gold_hit": f"{gold_hits}/{n}",
        "correct": f"{correct}/{n}" if generate else "—",
        "avg_chunk_tokens": int(_mean(chunk_tokens)),
        "avg_prompt_tokens": int(_mean(prompt_tokens)) if generate else "—",
        "avg_completion_tokens": int(_mean(completion_tokens)) if generate else "—",
        "avg_rerank_ms": _mean(rerank_ms),
        "avg_generate_s": _mean(generate_s) if generate else "—",
        "mean_gold_rank": round(_mean(gold_ranks), 2),
    }


def overfetch_anchor(retriever: BiEncoderRetriever, top_n: int, top_k: int) -> dict:
    """Tokens the raw first-stage top-N would dump in, vs the reranked top-k budget."""
    raw_topn_tokens = []
    for q in EVAL_QUERIES:
        cands, _ = retriever.retrieve(q.question, top_n=top_n)
        raw_topn_tokens.append(sum(count_tokens(c.doc.text) for c in cands))
        topk_tokens_est = sum(count_tokens(c.doc.text) for c in cands[:top_k])
    avg_topn = int(_mean(raw_topn_tokens))
    return {"top_n": top_n, "top_k": top_k, "avg_raw_topn_tokens": avg_topn}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=FIRST_STAGE_TOP_N)
    ap.add_argument("--top-k", type=int, default=FINAL_TOP_K)
    ap.add_argument("--no-generate", action="store_true",
                    help="retrieval-only: skip Ollama (fast; reports gold-hit + tokens, not correctness)")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    quiet()
    generate = not args.no_generate

    corpus = build_corpus(n_distractors=N_DISTRACTORS, seed=CORPUS_SEED)
    print(f"Corpus: {corpus_stats(corpus)}  |  queries: {len(EVAL_QUERIES)}  |  model: {MODEL}")
    print("Embedding corpus (first stage, CPU) …")
    retriever = BiEncoderRetriever(corpus)
    print(f"  index built in {retriever.index_build_s}s")

    anchor = overfetch_anchor(retriever, args.top_n, args.top_k)
    print(f"\nOver-fetch anchor: first-stage top-{anchor['top_n']} dumps "
          f"~{anchor['avg_raw_topn_tokens']} chunk tokens into the window on average. "
          f"Reranking keeps only top-{anchor['top_k']}.")

    rerankers = list(RERANKERS)
    if COHERE_API_KEY and "cohere" not in rerankers:
        rerankers.append("cohere")
    elif not COHERE_API_KEY:
        print("(COHERE_API_KEY not set → skipping the off-premises Config D)")

    results = [run_config(r, retriever, args.top_n, args.top_k, generate) for r in rerankers]

    # Printed table kept to 7 readable columns; full token in/out, mean gold
    # rank, and per-query detail all persist to results_abc.json via --save.
    headers = ["reranker", "local", "gold-hit", "correct", "chunk tok", "rerank ms", "gen s"]
    rows = [[r["reranker"], "yes" if r["local"] else "off-prem", r["gold_hit"],
             r["correct"], r["avg_chunk_tokens"], r["avg_rerank_ms"],
             r["avg_generate_s"]] for r in results]
    print()
    print_table(
        f"A/B/C config table  |  top_n={args.top_n} top_k={args.top_k}  |  {MODEL}",
        headers, rows,
        caption="gold-hit = correct chunk survived into top-k (the reranker).  "
                "correct = answer contained the gold fact (end-to-end).  "
                "Full token in/out + mean gold rank → results_abc.json.")

    if args.save:
        save_results("results_abc.json",
                     {"model": MODEL, "anchor": anchor, "top_n": args.top_n,
                      "top_k": args.top_k, "configs": results})


if __name__ == "__main__":
    main()
