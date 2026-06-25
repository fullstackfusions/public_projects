"""
Multi-agent LangGraph pipeline for the real-PDF reranking experiment.

Four specialized agents, each a named LangGraph node, with a clear contract:

  retrieval_agent  — bi-encoder first stage, top-N candidates from the full
                     index.  The over-fetcher: fast, cheap, but order is noisy.

  reranker_agent   — cross-encoder second stage, re-scores every candidate
                     jointly with the query and keeps only the top-k.

  compress_agent   — SmartCrusher (Headroom rule-based): squeezes structure out
                     of the survivors before handing them to the LLM.

  answer_agent     — ChatOllama (qwen3:8b, local): generates the final answer
                     from the compressed, reranked context, capturing Ollama's
                     own token counts for accurate reporting.

Each agent prints a one-line log on what it saw and produced, so the pipeline
is transparent when running interactively.

Usage (via Pipeline class):
  retriever = BiEncoderRetriever()
  pipe = Pipeline(retriever, get_reranker("bge"))
  result = pipe.run("What is the Sharpe ratio?", top_n=30, top_k=5)
"""

from __future__ import annotations

import time
import re
from typing import TypedDict, Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

from projects.local_first_reranking_layer.giant_testing.config import (
    MODEL, OLLAMA_BASE_URL, SYSTEM_PROMPT, DISABLE_THINKING,
    FIRST_STAGE_TOP_N, FINAL_TOP_K,
)
from projects.local_first_reranking_layer.giant_testing.retrieval import (
    BiEncoderRetriever, Candidate,
)
from projects.local_first_reranking_layer.giant_testing.rerankers import NoReranker
from projects.local_first_reranking_layer.giant_testing.compress import compress_chunks, count_tokens

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


# ---------------------------------------------------------------------------
# Shared state schema
# ---------------------------------------------------------------------------

class PipelineState(TypedDict, total=False):
    # ── inputs ──────────────────────────────────────────────────────────────
    query: str
    top_n: int
    top_k: int

    # ── retrieval_agent ──────────────────────────────────────────────────────
    candidates: list[Candidate]      # top-N from bi-encoder, un-reranked
    retrieve_latency_s: float
    first_stage_tokens: int          # total chunk tokens in the raw top-N

    # ── reranker_agent ───────────────────────────────────────────────────────
    kept: list[Candidate]            # top-k after reranking
    rerank_latency_s: float
    sources_kept: list[str]          # which PDFs survived into top-k

    # ── compress_agent ───────────────────────────────────────────────────────
    sent_texts: list[str]
    tokens_before_compress: int
    tokens_after_compress: int
    transforms_applied: list[str]

    # ── answer_agent ─────────────────────────────────────────────────────────
    answer: str
    answer_clean: str                # <think> stripped
    prompt_tokens: int               # Ollama-reported (includes system + context + question)
    completion_tokens: int
    generate_latency_s: float


# ---------------------------------------------------------------------------
# Agent node builders (close over retriever + reranker at graph-compile time)
# ---------------------------------------------------------------------------

def _make_retrieval_agent(retriever: BiEncoderRetriever):
    def retrieval_agent(state: PipelineState) -> PipelineState:
        query  = state["query"]
        top_n  = state.get("top_n", FIRST_STAGE_TOP_N)
        cands, elapsed = retriever.retrieve(query, top_n=top_n)
        first_stage_tok = sum(count_tokens(c.chunk.text) for c in cands)
        sources = sorted({c.chunk.source for c in cands})
        print(f"  [retrieval_agent]  top-{top_n} candidates | "
              f"{first_stage_tok} chunk tokens | sources: {sources}")
        return {
            **state,
            "candidates": cands,
            "retrieve_latency_s": elapsed,
            "first_stage_tokens": first_stage_tok,
        }
    return retrieval_agent


def _make_reranker_agent(reranker):
    def reranker_agent(state: PipelineState) -> PipelineState:
        query  = state["query"]
        top_k  = state.get("top_k", FINAL_TOP_K)
        result = reranker.rerank(query, state["candidates"], top_k=top_k)
        sources_kept = sorted({c.chunk.source for c in result.kept})
        kept_tok = sum(count_tokens(c.chunk.text) for c in result.kept)
        pages = [(c.chunk.source, c.chunk.page_start) for c in result.kept]
        print(f"  [reranker_agent]   {reranker.name} | top-{top_k} kept | "
              f"{kept_tok} chunk tokens | {reranker.local and 'local' or 'off-prem'} | "
              f"{result.latency_s*1000:.0f}ms | pages: {pages}")
        return {
            **state,
            "kept": result.kept,
            "rerank_latency_s": result.latency_s,
            "sources_kept": sources_kept,
        }
    return reranker_agent


def _compress_agent(state: PipelineState) -> PipelineState:
    comp = compress_chunks(state["kept"])
    print(f"  [compress_agent]   SmartCrusher | "
          f"{comp['tokens_before']}→{comp['tokens_after']} tok | "
          f"transforms: {comp['transforms'] or ['noop']}")
    return {
        **state,
        "sent_texts": comp["texts"],
        "tokens_before_compress": comp["tokens_before"],
        "tokens_after_compress": comp["tokens_after"],
        "transforms_applied": comp["transforms"],
    }


def _answer_agent(state: PipelineState) -> PipelineState:
    llm = ChatOllama(model=MODEL, base_url=OLLAMA_BASE_URL, temperature=0.1)

    context = "\n\n---\n\n".join(
        f"[chunk {i+1} | {state['kept'][i].chunk.source} "
        f"p{state['kept'][i].chunk.page_start}]\n{t}"
        for i, t in enumerate(state["sent_texts"])
    )
    user_text = f"Context:\n{context}\n\nQuestion: {state['query']}"
    if DISABLE_THINKING:
        user_text += " /no_think"

    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_text)]

    t0 = time.perf_counter()
    resp = llm.invoke(messages)
    elapsed = time.perf_counter() - t0

    meta = resp.response_metadata or {}
    prompt_tok = meta.get("prompt_eval_count", 0)
    completion_tok = meta.get("eval_count", 0)
    clean = _THINK_RE.sub("", resp.content or "").strip()

    print(f"  [answer_agent]     {MODEL} | "
          f"prompt={prompt_tok} out={completion_tok} tok | {elapsed:.1f}s")

    return {
        **state,
        "answer": resp.content,
        "answer_clean": clean,
        "prompt_tokens": prompt_tok,
        "completion_tokens": completion_tok,
        "generate_latency_s": elapsed,
    }


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------

def _build_graph(retriever: BiEncoderRetriever, reranker) -> object:
    g = StateGraph(PipelineState)
    g.add_node("retrieval_agent", _make_retrieval_agent(retriever))
    g.add_node("reranker_agent",  _make_reranker_agent(reranker))
    g.add_node("compress_agent",  _compress_agent)
    g.add_node("answer_agent",    _answer_agent)
    g.set_entry_point("retrieval_agent")
    g.add_edge("retrieval_agent", "reranker_agent")
    g.add_edge("reranker_agent",  "compress_agent")
    g.add_edge("compress_agent",  "answer_agent")
    g.add_edge("answer_agent",    END)
    return g.compile()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class Pipeline:
    """One retriever (shared), one swappable reranker, one compiled graph."""

    def __init__(self, retriever: BiEncoderRetriever, reranker):
        self.retriever = retriever
        self.reranker  = reranker
        self._graph    = _build_graph(retriever, reranker)

    def run(self, query: str, top_n: int = FIRST_STAGE_TOP_N,
            top_k: int = FINAL_TOP_K, generate: bool = True) -> PipelineState:
        """
        Run the full agent pipeline for one query.
        generate=False skips the answer_agent (fast retrieval+rerank only).
        """
        if generate:
            return self._graph.invoke({"query": query, "top_n": top_n, "top_k": top_k})

        # Retrieval-only: exercise all agents except answer_agent.
        state: PipelineState = {"query": query, "top_n": top_n, "top_k": top_k}
        cands, r_s = self.retriever.retrieve(query, top_n=top_n)
        first_tok = sum(count_tokens(c.chunk.text) for c in cands)
        state = {**state, "candidates": cands, "retrieve_latency_s": r_s,
                 "first_stage_tokens": first_tok}
        rr = self.reranker.rerank(query, cands, top_k=top_k)
        state = {**state, "kept": rr.kept, "rerank_latency_s": rr.latency_s,
                 "sources_kept": sorted({c.chunk.source for c in rr.kept})}
        comp = compress_chunks(rr.kept)
        return {
            **state,
            "sent_texts": comp["texts"],
            "tokens_before_compress": comp["tokens_before"],
            "tokens_after_compress": comp["tokens_after"],
            "transforms_applied": comp["transforms"],
            "answer": "", "answer_clean": "",
            "prompt_tokens": 0, "completion_tokens": 0, "generate_latency_s": 0.0,
        }
