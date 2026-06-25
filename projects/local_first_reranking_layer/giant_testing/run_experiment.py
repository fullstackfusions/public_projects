"""
Real-world reranking experiment over two PDFs (~1,030 chunks, ~464K tokens).

Three experiment modes, all runnable from the command line:

  --mode abc      A/B/C config table: same query set, fixed top-k, varies reranker.
                  Shows which reranker surfaces the most relevant chunks and at what latency.

  --mode ksweep   k-sweep: fix the best local reranker (bge), tighten top-k from 20 → 1.
                  Shows how many tokens you can cut before correctness degrades.
                  THIS is the "why did all those tokens arrive?" answer at real scale.

  --mode both     run abc then ksweep (default)

Run ingest.py FIRST if the index doesn't exist yet.

Usage:
  python -m projects.local_first_reranking_layer.giant_testing.run_experiment
  python -m projects.local_first_reranking_layer.giant_testing.run_experiment --mode ksweep --no-generate
  python -m projects.local_first_reranking_layer.giant_testing.run_experiment --mode abc --top-k 5 --save
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from projects.local_first_reranking_layer.giant_testing._quiet import quiet
from projects.local_first_reranking_layer.giant_testing.config import (
    MODEL, RERANKERS, COHERE_API_KEY, FIRST_STAGE_TOP_N, FINAL_TOP_K,
    K_SWEEP_VALUES, INDEX_DIR,
)
from projects.local_first_reranking_layer.giant_testing.retrieval import BiEncoderRetriever
from projects.local_first_reranking_layer.giant_testing.rerankers import get_reranker
from projects.local_first_reranking_layer.giant_testing.graph import Pipeline
from projects.local_first_reranking_layer.giant_testing.eval_queries import EVAL_QUERIES, Query
from projects.local_first_reranking_layer.giant_testing.compress import count_tokens


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mean(xs: list) -> float:
    return round(statistics.mean(xs), 1) if xs else 0.0


def _is_correct(query: Query, answer: str) -> bool:
    text = answer.lower()
    return any(g.lower() in text for g in query.gold)


def _source_diversity(kept) -> str:
    """Count distinct PDF sources in the kept set."""
    sources = {c.chunk.source for c in kept}
    return f"{len(sources)} src"


def _print_table(title: str, headers: list[str], rows: list[list],
                 caption: str | None = None):
    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box
        t = Table(title=title, box=box.ROUNDED, show_lines=False, caption=caption)
        for i, h in enumerate(headers):
            t.add_column(h, justify="left" if i == 0 else "right",
                         style="cyan" if i == 0 else None)
        for r in rows:
            t.add_row(*[str(c) for c in r])
        Console().print(t)
    except ImportError:
        print(f"\n=== {title} ===")
        col_w = [max(len(str(h)), *(len(str(r[i])) for r in rows))
                 for i, h in enumerate(headers)]
        print("  ".join(str(h).ljust(col_w[i]) for i, h in enumerate(headers)))
        print("-" * sum(col_w))
        for r in rows:
            print("  ".join(str(r[i]).ljust(col_w[i]) for i in range(len(headers))))
        if caption:
            print(caption)


# ---------------------------------------------------------------------------
# A/B/C: fixed top-k, vary reranker
# ---------------------------------------------------------------------------

def run_abc(retriever: BiEncoderRetriever, top_n: int, top_k: int,
            generate: bool, reranker_names: list[str]) -> list[dict]:
    results = []
    for name in reranker_names:
        rr = get_reranker(name)
        pipe = Pipeline(retriever, rr)

        correct = 0
        chunk_tok_sent, prompt_tok, rerank_ms, gen_s = [], [], [], []
        first_stage_tok_list, src_diversity = [], []

        print(f"\n{'─'*60}")
        print(f"Config: {name.upper()}  (local={rr.local})")
        print(f"{'─'*60}")

        for q in EVAL_QUERIES:
            state = pipe.run(q.question, top_n=top_n, top_k=top_k, generate=generate)
            tok_sent = state.get("tokens_after_compress", 0)
            chunk_tok_sent.append(tok_sent)
            first_stage_tok_list.append(state.get("first_stage_tokens", 0))
            rerank_ms.append(state.get("rerank_latency_s", 0) * 1000)
            src_diversity.append(_source_diversity(state["kept"]))

            ok = "—"
            if generate:
                ok_bool = _is_correct(q, state.get("answer_clean", ""))
                correct += int(ok_bool)
                prompt_tok.append(state.get("prompt_tokens", 0))
                gen_s.append(state.get("generate_latency_s", 0))
                ok = "✓" if ok_bool else "✗"

            print(f"  {q.id:<18} sent={tok_sent:>4} tok | "
                  f"src={_source_diversity(state['kept'])} | correct={ok}")

        n = len(EVAL_QUERIES)
        results.append({
            "reranker": name,
            "local": rr.local,
            "correct": f"{correct}/{n}" if generate else "—",
            "avg_first_stage_tok": int(_mean(first_stage_tok_list)),
            "avg_sent_tok": int(_mean(chunk_tok_sent)),
            "avg_prompt_tok": int(_mean(prompt_tok)) if generate else "—",
            "avg_rerank_ms": round(_mean(rerank_ms), 1),
            "avg_gen_s": round(_mean(gen_s), 1) if generate else "—",
        })

    return results


# ---------------------------------------------------------------------------
# k-sweep: fix reranker, vary top-k
# ---------------------------------------------------------------------------

def run_ksweep(retriever: BiEncoderRetriever, reranker_name: str,
               top_n: int, k_values: list[int], generate: bool) -> list[dict]:
    rr = get_reranker(reranker_name)
    pipe = Pipeline(retriever, rr)
    results = []

    for k in k_values:
        print(f"\n── top_k = {k} " + "─" * 40)
        correct = 0
        sent_tok, prompt_tok = [], []
        for q in EVAL_QUERIES:
            state = pipe.run(q.question, top_n=top_n, top_k=k, generate=generate)
            sent_tok.append(state.get("tokens_after_compress", 0))
            ok = "—"
            if generate:
                ok_bool = _is_correct(q, state.get("answer_clean", ""))
                correct += int(ok_bool)
                prompt_tok.append(state.get("prompt_tokens", 0))
                ok = "✓" if ok_bool else "✗"
            print(f"  {q.id:<18} sent={state.get('tokens_after_compress',0):>4} tok | correct={ok}")

        n = len(EVAL_QUERIES)
        results.append({
            "top_k": k,
            "correct": f"{correct}/{n}" if generate else "—",
            "avg_sent_tok": int(_mean(sent_tok)),
            "avg_prompt_tok": int(_mean(prompt_tok)) if generate else "—",
        })

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["abc", "ksweep", "both"], default="both")
    ap.add_argument("--top-n",  type=int, default=FIRST_STAGE_TOP_N)
    ap.add_argument("--top-k",  type=int, default=FINAL_TOP_K,
                    help="fixed top-k for abc mode")
    ap.add_argument("--sweep-reranker", default="bge",
                    choices=["none", "flashrank", "bge"],
                    help="reranker held fixed in k-sweep mode")
    ap.add_argument("--no-generate", action="store_true",
                    help="skip LLM generation (fast; reports tokens only, not correctness)")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    quiet()
    generate = not args.no_generate

    # ── Load index ──────────────────────────────────────────────────────────
    manifest_path = INDEX_DIR / "manifest.json"
    if not manifest_path.exists():
        print("Index not found. Run ingest first:")
        print("  python -m projects.local_first_reranking_layer.giant_testing.ingest")
        return

    manifest = json.loads(manifest_path.read_text())
    total_chunks = manifest["total_chunks"]
    total_tokens = manifest["total_tokens"]
    print(f"\nIndex: {total_chunks} chunks | {total_tokens:,} total tokens | model: {MODEL}")
    print(f"Sources:")
    for s in manifest["sources"]:
        print(f"  {s['file']}: {s['chunks']} chunks, {s['tokens']:,} tok, {s['pages']} pages")

    # One retriever shared across all configs — avoid re-embedding per config.
    print("\nLoading retriever …")
    retriever = BiEncoderRetriever()

    # Compute naive upper bound: what raw top-N dumps
    print(f"\nSampling first-stage raw top-{args.top_n} token counts …")
    raw_samples = []
    from projects.local_first_reranking_layer.giant_testing.rerankers import NoReranker
    _nr = NoReranker()
    _pipe_nr = Pipeline(retriever, _nr)
    for q in EVAL_QUERIES[:4]:   # sample 4 queries for the anchor
        state = _pipe_nr.run(q.question, top_n=args.top_n, top_k=args.top_n, generate=False)
        raw_samples.append(state.get("first_stage_tokens", 0))
    avg_raw_topn = int(_mean(raw_samples))
    print(f"  First-stage top-{args.top_n} (uncut): ~{avg_raw_topn} chunk tokens on average")
    print(f"  Full corpus (stuff-everything): {total_tokens:,} tokens")
    print(f"  After rerank+top-{args.top_k}: will appear in table below")

    reranker_names = list(RERANKERS)
    if COHERE_API_KEY and "cohere" not in reranker_names:
        reranker_names.append("cohere")

    saved: dict = {"model": MODEL, "manifest": manifest,
                   "top_n": args.top_n, "anchor_avg_raw_topn_tok": avg_raw_topn}

    # ── A/B/C table ──────────────────────────────────────────────────────────
    if args.mode in ("abc", "both"):
        print(f"\n{'═'*60}")
        print(f"A/B/C CONFIG TABLE  |  top_n={args.top_n}  top_k={args.top_k}")
        print(f"{'═'*60}")
        abc_results = run_abc(retriever, args.top_n, args.top_k, generate, reranker_names)

        headers = ["reranker", "local", "correct", "1st-stage tok", "sent tok", "rerank ms", "gen s"]
        rows = [[r["reranker"], "yes" if r["local"] else "off-prem", r["correct"],
                 r["avg_first_stage_tok"], r["avg_sent_tok"],
                 r["avg_rerank_ms"], r["avg_gen_s"]] for r in abc_results]
        _print_table(
            f"A/B/C  |  top_n={args.top_n}  top_k={args.top_k}  |  {MODEL}",
            headers, rows,
            caption=(
                f"1st-stage tok = avg chunk tokens in raw top-{args.top_n} (before rerank).  "
                f"sent tok = after rerank→top-{args.top_k}→SmartCrusher.  "
                f"Full corpus = {total_tokens:,} tok."
            )
        )
        saved["abc"] = abc_results

    # ── k-sweep table ─────────────────────────────────────────────────────────
    if args.mode in ("ksweep", "both"):
        print(f"\n{'═'*60}")
        print(f"K-SWEEP  |  reranker={args.sweep_reranker}  top_n={args.top_n}")
        print(f"{'═'*60}")
        ksweep_results = run_ksweep(
            retriever, args.sweep_reranker, args.top_n, K_SWEEP_VALUES, generate)

        headers = ["top_k", "correct", "sent tok", "prompt tok"]
        rows = [[r["top_k"], r["correct"], r["avg_sent_tok"], r["avg_prompt_tok"]]
                for r in ksweep_results]
        _print_table(
            f"k-sweep  |  reranker={args.sweep_reranker}  |  {MODEL}",
            headers, rows,
            caption=(
                f"Full corpus = {total_tokens:,} tok.  "
                f"1st-stage raw top-{args.top_n} ≈ {avg_raw_topn} tok.  "
                f"sent tok = reranked top-k after SmartCrusher."
            )
        )
        saved["ksweep"] = ksweep_results

    if args.save:
        out = INDEX_DIR.parent / "results_giant.json"
        # Merge with any existing results so running --mode abc and --mode
        # ksweep in separate invocations does not clobber each other.
        if out.exists():
            try:
                existing = json.loads(out.read_text())
            except (json.JSONDecodeError, OSError):
                existing = {}
            existing.update(saved)
            saved = existing
        out.write_text(json.dumps(saved, indent=2, default=str))
        print(f"\nSaved → {out}")


if __name__ == "__main__":
    main()
