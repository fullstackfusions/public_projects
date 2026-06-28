# Local-First Session Layer — Cross-Session Memory (Part 6)

Declarative + procedural memory with a closed provenance chain, running entirely
local: **Qwen3 8B (reasoning)** on Ollama, **Mem0** over **pgvector**, a
**SKILL.md** procedural layer, and a four-agent harness.

Two sessions, one experiment:

- **Session A** retrieves from the Part 5 corpus, *reasons* over it with Qwen3,
  *verifies* the finding, *extracts* durable facts, and writes them to Mem0 with
  provenance metadata.
- **Session B** opens a fresh context with a differently-worded query, retrieves
  the relevant facts from Mem0 (never touching the 530K-token corpus), and
  answers. We then verify the provenance chain closes and measure the
  compression ratio from session tokens to stored facts.

> Adapted from the Part 6 guide, which defaulted to `qwen2.5:7b`. This build runs
> on **`qwen3:8b`** — a hybrid *reasoning* model — because the experiment is about
> what an agent decides and remembers, and the reasoning trace is part of that.

---

## Architecture

```
Session A  (write path)
  RetrieverAgent ─▶ ReasonerAgent ─▶ VerifierAgent ─▶ ExtractorAgent ─▶ Mem0.add()
   Part 5 chunk     Qwen3 (think on)  EVALUATOR        ~session→facts    + provenance
                                      pattern (Part 1) (compression)      metadata

Session B  (read path, fresh context)
  Mem0.search() ─▶ prompt_builder ─▶ Qwen3 (think on) ─▶ answer
   by similarity   SKILL.md (det.)                       no corpus hit
                   + facts (prob.)

Provenance chain (verified end-to-end):
  Session B output → Mem0 fact → Session A trace → CCR content → source doc
```

Two kinds of memory, deliberately on different paths:

| Memory | Path | Nature | Lives in |
|---|---|---|---|
| **Procedural** | injected verbatim every session | deterministic | `skills/compliance_report_format.md` |
| **Declarative** | surfaced by vector similarity | probabilistic | Mem0 + pgvector |

That split is the point: deterministic where you can be (format, rules,
verification), probabilistic only where you must (which remembered fact is
relevant to *this* query).

---

## Why a reasoning model changes the code

Qwen3 emits a `<think>…</think>` trace before its answer. The harness treats that
as a feature with a sharp edge:

- The **ReasonerAgent** runs with thinking **on** — better findings, and the
  trace is kept and carried into provenance.
- The **ExtractorAgent** runs with thinking **off** (`/no_think`), because it
  must return a clean JSON array; a reasoning trace in front of the JSON would
  break the parse.

`harness/reasoning.py` centralizes this: `split_thinking()` separates trace from
answer, and `chat(..., cfg=...)` toggles `/no_think` per call site
(`config.REASONER_REASONING` vs `config.EXTRACTOR_REASONING`).

---

## Project layout

```
local_first_session_layer/
├── config.py                       model selection, pgvector conn, reasoning toggles
├── docker-compose.yml              pgvector:pg16
├── setup.sh                        deps + pgvector + ollama pulls (idempotent)
├── requirements.txt
├── .env.example
├── skills/
│   └── compliance_report_format.md procedural memory (SKILL.md)
├── harness/
│   ├── reasoning.py                Qwen3 <think> handling + chat helper
│   ├── mem0_config.py              Mem0 → local pgvector + local Ollama
│   ├── fact_extractor.py           session → 3–8 durable facts (compression)
│   ├── prompt_builder.py           injects procedural + declarative memory
│   └── agents.py                   Retriever / Reasoner / Verifier / Extractor
├── sessions/
│   ├── session_a.py                retrieve → reason → verify → extract → store
│   └── session_b.py                cross-session retrieval → answer
├── verify_provenance.py            checks the chain closes (takes optional path arg)
└── results_session.example.json    shape reference (NOT measured numbers)
```

---

## Prerequisites

From Parts 1–5: Python 3.11+, Ollama, LangGraph, the Part 5 corpus index.
New for Part 6: Docker (for pgvector), `mem0ai`, `psycopg2-binary`, `langfuse`.

---

## Run it

```bash
# 0. one-shot: python deps + pgvector + vector extension + ollama pulls
./setup.sh

#    (or do it by hand)
# pip install -r requirements.txt --break-system-packages
# docker compose up -d
# docker compose exec pgvector psql -U mem0user -d mem0db -c "CREATE EXTENSION IF NOT EXISTS vector;"
# ollama pull qwen3:8b
# ollama pull nomic-embed-text

# 1. write path: retrieve + reason + verify + extract + store
python sessions/session_a.py

# 2. read path: cross-session retrieval (run AFTER session_a)
python sessions/session_b.py

# 3. verify the provenance chain closes
python verify_provenance.py

# 4. inspect
cat results_session.json | python -m json.tool
```

`results_session.json` is written by the run and is git-ignored — commit it
yourself once you have measured numbers you want to cite. `results_session.example.json`
shows the shape only; do **not** cite its numbers as results.

---

## What to measure

| Metric | Where |
|---|---|
| Compression ratio (session tokens ÷ facts) | `session_a.compression_ratio` |
| Retrieval accuracy (did B get the right fact?) | manual check on `retrieved_facts` |
| Provenance closure (all 3 metadata fields?) | `verify_provenance.py` |
| Cross-session consistency (B answer vs A finding) | compare answers |
| Corpus retrieval avoided | `session_b.corpus_retrieval_needed` |

After a run, add a `metrics` block to `results_session.json` (see the example file).

---

## The three questions Part 7 answers

- **Q1 — does declarative retrieval surface the right fact?** `QUERY_B` says
  "Tier 2" where Session A said "Category 2". If Mem0 still returns the 2.5%
  Category-2 fact, the embedder closed the vocabulary gap.
- **Q2 — does the provenance chain close?** Only if Session A wrote the metadata
  at storage time. `verify_provenance.py` is the check; the fix, if it breaks, is
  the metadata dict in `session_a.py`.
- **Q3 — failure mode on a wrong-fact retrieval?** Add a near-neighbor fact
  (e.g. "Category 3 buffer = 3.0%, 2024 revision") to Mem0 and re-run Session B.
  Whether it returns 2.5%/Cat-2/2026 or 3.0%/Cat-3/2024 is decided by embedding
  similarity — and where the probabilistic path can fail.

---

## Wiring to the rest of the stack

The `RetrieverAgent` ships with a faithful in-repo corpus sample so the demo runs
without re-indexing the Part 5 PDFs. To run against the real stack, replace
`RetrieverAgent.retrieve` (in `harness/agents.py`) with a call into
`local_first_reranking_layer`'s retrieval + BGE rerank pipeline — `ccr_content_id`
then comes from Headroom's CCR, `langfuse_trace_id` from the Part 1 harness, and
the rest is unchanged.

| Part | Provides |
|---|---|
| Part 1 `agent_harness` | EVALUATOR pattern (VerifierAgent), `langfuse_trace_id` |
| Part 2 `rust_token_killer` | wraps subprocess output in the retrieval step |
| Part 3 `local_first_compression_layer` | Headroom CCR → `ccr_content_id` |
| Part 5 `local_first_reranking_layer` | the corpus + BGE reranker (top_k chunk) |
| **Part 6** (this) | Mem0 + pgvector + SKILL.md + provenance metadata |
```
