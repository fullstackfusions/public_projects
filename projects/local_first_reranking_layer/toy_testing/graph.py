"""
The LangGraph pipeline for Part 4.

    retrieve ──► rerank ──► compress ──► generate
       │           │           │            │
   bi-encoder   cross-      SmartCrusher  ChatOllama
   top-N        encoder     (rule-based)  (local model)
                top-k

The reranker is the swappable node. Everything else is held constant across
configs so the table isolates one variable: retrieval quality.

A Pipeline binds a (already-embedded) retriever and a chosen reranker, then
compiles a graph whose nodes close over them. Build the retriever ONCE and
reuse it across rerankers — re-embedding the corpus per config would dominate
the wall clock and tell you nothing.
"""

from __future__ import annotations

import time
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

from projects.local_first_reranking_layer.config import (
    MODEL, OLLAMA_BASE_URL, SYSTEM_PROMPT, DISABLE_THINKING,
    FIRST_STAGE_TOP_N, FINAL_TOP_K,
)
from projects.local_first_reranking_layer.retrieval import BiEncoderRetriever, Candidate
from projects.local_first_reranking_layer.rerankers import BaseReranker
from projects.local_first_reranking_layer.compress import compress_chunks, count_tokens
from projects.local_first_reranking_layer.scoring import clean_answer


class PipeState(TypedDict, total=False):
    query: str
    top_n: int
    top_k: int
    candidates: list[Candidate]      # first-stage top-N
    kept: list[Candidate]            # post-rerank top-k
    sent_texts: list[str]            # post-compression chunk texts
    # metrics
    retrieve_s: float
    rerank_s: float
    generate_s: float
    tokens_chunks_raw: int           # tokens in kept chunks before SmartCrusher
    tokens_chunks_sent: int          # tokens in chunks actually sent
    prompt_tokens: int               # Ollama-reported input tokens (whole prompt)
    completion_tokens: int           # Ollama-reported output tokens
    transforms: list[str]
    answer: str


def build_pipeline_graph(retriever: BiEncoderRetriever, reranker: BaseReranker):
    """Compile a graph whose nodes close over a shared retriever + reranker."""

    def retrieve_node(state: PipeState) -> PipeState:
        candidates, elapsed = retriever.retrieve(
            state["query"], top_n=state.get("top_n", FIRST_STAGE_TOP_N))
        return {**state, "candidates": candidates, "retrieve_s": elapsed}

    def rerank_node(state: PipeState) -> PipeState:
        result = reranker.rerank(
            state["query"], state["candidates"], top_k=state.get("top_k", FINAL_TOP_K))
        return {**state, "kept": result.kept, "rerank_s": result.latency_s}

    def compress_node(state: PipeState) -> PipeState:
        comp = compress_chunks(state["kept"])
        return {
            **state,
            "sent_texts": comp["texts"],
            "tokens_chunks_raw": comp["tokens_before"],
            "tokens_chunks_sent": comp["tokens_after"],
            "transforms": comp["transforms"],
        }

    def generate_node(state: PipeState) -> PipeState:
        llm = ChatOllama(model=MODEL, base_url=OLLAMA_BASE_URL, temperature=0.1)

        context = "\n\n---\n\n".join(
            f"[chunk {i+1}]\n{t}" for i, t in enumerate(state["sent_texts"]))
        user = f"Context:\n{context}\n\nQuestion: {state['query']}"
        if DISABLE_THINKING:
            user += " /no_think"

        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user)]

        t0 = time.perf_counter()
        resp = llm.invoke(messages)
        elapsed = time.perf_counter() - t0

        meta = resp.response_metadata or {}
        return {
            **state,
            "generate_s": elapsed,
            "prompt_tokens": meta.get("prompt_eval_count", 0),
            "completion_tokens": meta.get("eval_count", 0),
            "answer": resp.content,
        }

    g = StateGraph(PipeState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("rerank", rerank_node)
    g.add_node("compress", compress_node)
    g.add_node("generate", generate_node)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "rerank")
    g.add_edge("rerank", "compress")
    g.add_edge("compress", "generate")
    g.add_edge("generate", END)
    return g.compile()


class Pipeline:
    """Reusable pipeline: one embedded corpus, a swappable reranker."""

    def __init__(self, retriever: BiEncoderRetriever, reranker: BaseReranker):
        self.retriever = retriever
        self.reranker = reranker
        self.graph = build_pipeline_graph(retriever, reranker)

    def run(self, query: str, top_n: int = FIRST_STAGE_TOP_N,
            top_k: int = FINAL_TOP_K, generate: bool = True) -> PipeState:
        """
        Run the pipeline for one query. With generate=False the graph still
        retrieves/reranks/compresses (so retrieval-quality and token metrics are
        produced) but skips the Ollama call — useful for fast retrieval-only sweeps.
        """
        init: PipeState = {"query": query, "top_n": top_n, "top_k": top_k}
        if generate:
            return self.graph.invoke(init)

        # retrieval-only path: reuse the same nodes without generate
        state = init
        candidates, r_s = self.retriever.retrieve(query, top_n=top_n)
        state = {**state, "candidates": candidates, "retrieve_s": r_s}
        rr = self.reranker.rerank(query, candidates, top_k=top_k)
        state = {**state, "kept": rr.kept, "rerank_s": rr.latency_s}
        comp = compress_chunks(rr.kept)
        state = {**state, "sent_texts": comp["texts"],
                 "tokens_chunks_raw": comp["tokens_before"],
                 "tokens_chunks_sent": comp["tokens_after"],
                 "transforms": comp["transforms"], "answer": "",
                 "generate_s": 0.0, "prompt_tokens": 0, "completion_tokens": 0}
        return state
