# Local-First Reranking Layer — Part 4 Hands-on

> **Series question this part answers:** *Why did 3,496 tokens arrive in the first place?*

Part 3 ([`local_first_compression_layer`](../local_first_compression_layer)) showed how to
*compress* retrieved content once it's in the window. Part 4 goes one step
upstream and asks why so much content arrived at all. The answer is **retrieval
quality**: a cheap first-stage retriever over-fetches near-duplicates, and a
**reranker** is what trims the payload before it ever reaches the compression
layer.

```
Part 4 (this repo)            Part 3
┌───────────────────────────┐ ┌──────────────┐
│ retrieve ──► rerank ──────│►│ compress ────│► generate
│ bi-encoder  cross-encoder │ │ SmartCrusher │  ChatOllama
│ top-N       top-k         │ │ (rule-based) │  (local model)
└───────────────────────────┘ └──────────────┘
  "why did the tokens arrive"   "shrink what did"
```

Everything runs **on CPU** and downloads weights once, then stays fully local.
The only off-premises option is Cohere Rerank, which is **opt-in** and exists
purely to make the data-residency argument concrete — it is never required.

> **New here?** [EXPERIMENT.md](EXPERIMENT.md) is the full writeup — the
> hypothesis, the models, the methodology, the measured results, and what we
> concluded. This README is the how-to-run.

---

## The honest split: what's real vs. what you measure

This post's credibility is "what I actually measured." The scripts here produce
the numbers; the repo ships **no invented benchmark values**. Run them on your
hardware, your corpus, your model. The three `[measure]` cells map to three
scripts:

| `[measure]` cell | Script | What it produces |
|---|---|---|
| A/B/C config table | [`run_abc.py`](run_abc.py) | gold-hit, correctness, tokens, latency per reranker at fixed *k* |
| k-sweep table | [`run_ksweep.py`](run_ksweep.py) | how quality holds as you tighten top-10 → 5 → 3 → 1 |
| cold-start timing | [`bench_coldstart.py`](bench_coldstart.py) | FlashRank model-load vs. warm per-pair latency |

---

## Why three local rerankers, not "FlashRank vs. Cohere"

The draft framed it as FlashRank (lightweight, local) vs. Cohere (quality,
off-premises) — a false trade-off. There's a third category: **open-weight
cross-encoders you self-host**, which give you neural-reranker quality *and* keep
everything on your own compute. So the experiment is a spectrum:

```
none        → first-stage order only (the over-fetch, unfixed)      Config A
flashrank   → tiny ONNX cross-encoder, CPU, deterministic, local    Config B
bge         → bge-reranker-v2-m3, neural, CPU, Apache-2.0, local     Config C  ← the winner for compliance
cohere      → hosted API, off-premises ✗ for data residency         Config D  (opt-in)
```

The middle column — **neural-quality reranking with nothing leaving the box** —
is the principal-engineer conclusion. "Use the lightweight one for residency
reasons" undersells what's actually available locally.

| Reranker | Type | Runs where | License | Notes |
|---|---|---|---|---|
| `ms-marco-MiniLM-L-12-v2` (FlashRank) | cross-encoder | CPU, local | Apache-2.0 | tiny, deterministic, ~1ms/pair warm |
| `bge-reranker-v2-m3` (BAAI) | cross-encoder | CPU, local | Apache-2.0 | multilingual, strong baseline; swap to `bge-reranker-base` for speed |
| `rerank-v3.5` (Cohere) | cross-encoder | **API, off-prem** | proprietary | every candidate leaves the machine |

---

## Bi-encoder vs. cross-encoder (the mechanism — not a measurement)

- **First stage = bi-encoder.** Embeds query and each document *independently*,
  ranks by cosine similarity. Fast and cheap because document vectors are
  precomputed, but it has **no cross-attention** between query and document — so
  for "transaction record retention" it cannot tell *completed* records from
  *pending* ones and drags both into the top-N.
- **Rerank stage = cross-encoder.** Scores `(query, document)` **jointly** with
  full attention. Far more accurate at ordering, too expensive to run over a
  whole corpus — so it only ever re-scores the first stage's top-N candidates.

The corpus in [`data/corpus.py`](data/corpus.py) is built to expose exactly this
gap: each gold chunk is surrounded by **hundreds of adversarial near-twins** that
share its head noun phrase and differ in one qualifier (`completed` vs `pending`,
`at rest` vs `in transit`, core-banking `RPO` vs `RTO`). The bi-encoder scatters
the gold chunk to ranks 4–6; the cross-encoder pulls it back to rank 1.

---

## Setup

```bash
# 1. Generation model on Ollama (reasoning model; we disable thinking with /no_think)
ollama pull qwen3:8b          # documented default (5.2 GB)
# ollama pull qwen2.5:7b      # faster non-reasoning fallback

# 2. Python deps (CPU torch is fine — no GPU needed anywhere)
pip install -r requirements.txt
```

First run downloads, once: the bi-encoder (`all-MiniLM-L6-v2`, ~80 MB),
FlashRank's ONNX model (~22 MB), and `bge-reranker-v2-m3` (~2.3 GB).

To enable the off-premises Config D:

```bash
pip install cohere
export COHERE_API_KEY=...     # without this, Config D is silently skipped
```

---

## Run it

All scripts are run as modules from the **repo root** (so the
`projects.local_first_reranking_layer` package resolves):

```bash
# [measure] #1 — A/B/C(/D) config table at a fixed top-k
python -m projects.local_first_reranking_layer.run_abc --top-k 5 --save

# fast retrieval-only variant (skips Ollama; reports gold-hit + tokens, not correctness)
python -m projects.local_first_reranking_layer.run_abc --no-generate

# [measure] #2 — k-sweep with the best local reranker
python -m projects.local_first_reranking_layer.run_ksweep --reranker bge --save

# [measure] #3 — FlashRank cold-start vs warm latency
python -m projects.local_first_reranking_layer.bench_coldstart --warm-runs 30
```

### Reading the tables

Two metrics are reported separately on purpose, because they fail for different
reasons:

- **gold-hit@k** — did the *one* correct chunk survive into the top-k actually
  sent to the model? This isolates the **reranker**.
- **correct** — did the model's final answer contain the gold fact? This is the
  **end-to-end** result.

If `gold-hit` is high but `correct` is low, the model fumbled a chunk it was
given (a generation problem). If `gold-hit` itself falls, the reranker dropped
the answer (a retrieval problem). `mean gold rank` shows how aggressively each
reranker pushes the correct chunk toward position 1 — the lever that makes a
small *k* safe in the k-sweep.

---

## Files

| File | Role |
|---|---|
| [`config.py`](config.py) | models, top-N / top-k, corpus size, all knobs |
| [`data/corpus.py`](data/corpus.py) | gold chunks + adversarial near-twin distractors + eval queries |
| [`retrieval.py`](retrieval.py) | CPU bi-encoder first stage (the over-fetcher) |
| [`rerankers.py`](rerankers.py) | `none` / `flashrank` / `bge` / `cohere` behind one interface |
| [`compress.py`](compress.py) | SmartCrusher (Part 3 carry-over) over the survivors |
| [`scoring.py`](scoring.py) | correctness + gold-hit@k + gold-rank |
| [`graph.py`](graph.py) | the LangGraph pipeline, reranker as the swappable node |
| [`run_abc.py`](run_abc.py) · [`run_ksweep.py`](run_ksweep.py) · [`bench_coldstart.py`](bench_coldstart.py) | the three `[measure]` runners |

---

## How this composes with Part 3

Reranking and compression target **different waste**. Reranking removes *whole
irrelevant chunks* (the over-fetch); SmartCrusher squeezes *structure* out of the
chunks that remain. On this prose-heavy retrieval corpus SmartCrusher often
no-ops (prose has little structural redundancy to strip) — and that's the point:
the Part-4 lever is *which* chunks arrive and *how few*, which is why the k-sweep,
not the compression delta, carries the token story here. Wire both and you pay
for the fewest, smallest, most-relevant tokens — the full local-first stack.
