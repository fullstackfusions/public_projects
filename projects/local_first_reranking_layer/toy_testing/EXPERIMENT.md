# Experiment Writeup — Local-First Reranking (Part 4)

A developer's guide to *what* this experiment tests, *how* it's built, and *what
it concluded*. If you just want to run it, see the [README](README.md); this
document is the reasoning behind the code.

---

## TL;DR

A cheap first-stage retriever (a bi-encoder) **over-fetches**: for a question
buried in a corpus of near-identical look-alikes, it drags the wrong chunks into
the model's context window alongside the right one. A **reranker** (a
cross-encoder, run on CPU) fixes the ordering. We measured three things:

1. **At a fixed budget**, a reranker consolidates the correct chunk from an
   average rank of **~2.9 → 1.0**, lifting end-to-end correctness from **7/8 → 8/8**.
2. **The reranker lets you shrink the budget**: with a trusted reranker you can
   drop from top-10 to **top-1** and still answer **7/8** correctly — cutting the
   retrieved payload from **510 → 62 tokens (~8×)**.
3. **The cost is affordable and local**: FlashRank reranks 20 candidates in
   **~29ms** warm (a one-time ~83ms model load); the neural BGE reranker is
   heavier (~0.7s/query) but runs entirely on CPU with nothing leaving the box.

**Conclusion:** retrieval quality is *why* a downstream compression layer (Part 3)
had thousands of tokens to compress in the first place. Reranking is the upstream
fix, and a **self-hosted neural cross-encoder gives Cohere-class ordering with
zero data egress** — the right default for a data-residency constraint.

---

## 1. The question

This is Part 4 of a 6-part series on agent context engineering. Each part
isolates one boundary where tokens leak into an agent's context and the tool that
plugs it:

| Part | Boundary | Question it answers |
|---|---|---|
| 3 | Content (in-session) | Why does retrieved content cost 3,496 tokens *after* compression? |
| **4 (this)** | **Retrieval quality** | **Why did those 3,496 tokens arrive in the first place?** |

Part 3 compressed whatever showed up in the window. Part 4 steps upstream and
asks why so much showed up. The answer is retrieval quality, and the fix is
reranking — applied *before* the compression layer ever sees the content.

---

## 2. Hypothesis

> A bi-encoder first stage cannot distinguish a correct chunk from lexically
> similar distractors, so it over-fetches. A cross-encoder reranker, reading
> (query, document) jointly, restores the correct ordering — which (a) raises
> answer correctness at a fixed token budget, and (b) makes a much smaller token
> budget viable without losing correctness.

And, operationally:

> Neural-quality reranking does not require a hosted API. An open-weight
> cross-encoder run on CPU keeps all data on-premises while matching the ordering
> quality you'd otherwise reach for Cohere to get.

---

## 3. System under test

### Pipeline (LangGraph)

```
retrieve ──► rerank ──► compress ──► generate
   │           │           │            │
bi-encoder  cross-      SmartCrusher  ChatOllama
top-N=20    encoder     (rule-based)  qwen3:8b
            top-k        (Part 3)      (local)
            ▲
            └─ the ONLY thing that changes between configs
```

The pipeline is a compiled `StateGraph` (see [graph.py](graph.py)); the generate
node calls a local model through `ChatOllama`. Everything except the reranker is
held constant so the experiment isolates one variable: **retrieval quality**.

### Models used

| Role | Model | Where it runs | Size | Why |
|---|---|---|---|---|
| First-stage retriever (bi-encoder) | `sentence-transformers/all-MiniLM-L6-v2` | CPU, local | ~80 MB | fast, cheap; precomputes doc vectors. The deliberate over-fetcher. |
| Reranker B (lightweight) | `ms-marco-MiniLM-L-12-v2` via **FlashRank** | CPU, local | ~22 MB | tiny ONNX cross-encoder, deterministic, ~1.4 ms/pair |
| Reranker C (neural) | `BAAI/bge-reranker-v2-m3` | CPU, local | ~2.3 GB | Apache-2.0, multilingual, Cohere-class ordering, **on-prem** |
| Reranker D (optional, contrast) | Cohere `rerank-v3.5` | **API, off-prem** | — | only runs if `COHERE_API_KEY` set; the data-residency counter-example |
| Generation | `qwen3:8b` (Ollama) | CPU/local | 5.2 GB | reasoning model; we pass `/no_think` to suppress the trace for clean scoring |
| Compression | Headroom **SmartCrusher** (rule-based) | CPU, local | — | Part 3 carry-over; squeezes structure from surviving chunks |
| Token counting | `tiktoken` (`cl100k_base`) | local | — | consistent pre-send estimates |

**Design choice worth calling out:** the original framing was "FlashRank
(lightweight, local) vs. Cohere (quality, off-prem)" — a false trade-off. We
added the middle column, a self-hosted neural cross-encoder (BGE), because it
delivers the quality *and* the residency. Cohere stays in as an opt-in contrast,
never a requirement.

### Bi-encoder vs. cross-encoder (the mechanism)

- **Bi-encoder (first stage):** embeds query and each document *independently*,
  ranks by cosine. Cheap because document vectors are precomputed — but with **no
  cross-attention**, it scores on bag-of-meaning overlap and can't tell
  *completed* transaction records from *pending* ones.
- **Cross-encoder (rerank):** scores `(query, document)` *jointly* with full
  attention. Far more accurate at ordering, too expensive to run over a whole
  corpus — so it only ever re-scores the first stage's top-N.

---

## 4. The corpus (why it's adversarial)

A reranking demo is only honest if the first stage genuinely struggles. Our first
corpus draft failed this: the bi-encoder scored **8/8** on its own, leaving
nothing for reranking to fix. So [data/corpus.py](data/corpus.py) is built to
expose the bi-encoder's blind spot:

- **8 gold chunks** — each a single, natural policy statement holding the one
  correct fact for one query (e.g. *"Completed customer transaction records must
  be retained for 7 years…"*). Deliberately **not** keyword-stuffed.
- **~240 adversarial near-twins** — sampled from ~377 generated distractors, each
  sharing the gold chunk's head noun phrase and differing in **one qualifier and
  the value**: *pending* vs *completed* records, *in transit* vs *at rest*
  encryption, core-banking **RTO** vs **RPO**, *Severity-2* vs *Severity-1*. None
  contain a gold fact.
- **2 JSON config chunks** — structured bloat, so SmartCrusher has something of
  its own kind to act on.

Everything is fictional ("Northbank"), so gold facts are defined by the corpus,
not by real regulation — which makes correctness scoring deterministic. The
corpus is seeded (`CORPUS_SEED=42`) for reproducibility.

**Effect:** with this corpus the bi-encoder scatters the gold chunk to ranks 4–6;
e.g. for the data-processor-approval query the gold chunk lands at **rank 6**,
outside a top-5 window entirely. That gap is what the reranker closes.

---

## 5. Experiments & methodology

Three runners, three `[measure]` cells in the post:

| Experiment | Script | Holds fixed | Varies | Answers |
|---|---|---|---|---|
| A/B/C config table | [run_abc.py](run_abc.py) | top-k=5 | the reranker | which reranker orders best, and at what latency |
| k-sweep | [run_ksweep.py](run_ksweep.py) | reranker (BGE) | top-k ∈ {10,5,3,1} | how few tokens can arrive before correctness breaks |
| cold-start | [bench_coldstart.py](bench_coldstart.py) | candidate set | warm vs cold | the one-time cost of loading a reranker |

### Two metrics, kept separate on purpose

| Metric | Measures | Fails when |
|---|---|---|
| **gold-hit@k** | did the *one* correct chunk survive into the top-k sent to the model? | the **reranker** dropped the answer (a retrieval failure) |
| **correct** | did the model's final answer contain the gold fact? | the **model** fumbled a chunk it was given (a generation failure) |

Reporting both lets you attribute a failure. A third diagnostic, **mean gold
rank**, shows how aggressively a reranker pushes the correct chunk toward
position 1 — the lever that makes a small *k* safe.

**Scoring** ([scoring.py](scoring.py)): `qwen3` `<think>…</think>` traces are
stripped before matching; an answer is correct if it contains any of the query's
gold tokens (case-insensitive). Gold values are distinctive (e.g. `7 year`,
`aes-256`, `72 hour`) and absent from same-topic distractors, so matches are
unambiguous.

---

## 6. Results

> Numbers below are from a representative **local CPU run** with `qwen3:8b`.
> Latency and exact token counts depend on your hardware and model — that's the
> point of running it yourself. The *shape* of the result is what's portable.

### 6.1 A/B/C config table (top-k = 5)

| reranker | local | gold-hit | correct | mean gold rank | rerank latency |
|---|---|---|---|---|---|
| none (first-stage only) | yes | 7/8 | 7/8 | **2.88** | 0 ms |
| flashrank | yes | 8/8 | 8/8 | **1.00** | ~56 ms/query |
| bge | yes | 8/8 | 8/8 | **1.38** | ~0.7 s/query |
| cohere | *off-prem* | *(only if `COHERE_API_KEY` set)* | | | network RTT |

**Read:** at an identical 5-chunk budget, both rerankers recover the one query the
bi-encoder lost (the rank-6 approval chunk) and collapse the mean gold rank toward
1. The cost is latency: FlashRank is nearly free; BGE is ~0.7 s/query on CPU —
the price of a neural model with no GPU.

### 6.2 k-sweep (reranker = BGE)

| top_k | gold-hit | correct | chunk tokens (arrived) | prompt tokens |
|---|---|---|---|---|
| 10 | 8/8 | 8/8 | 510 | 441 |
| 5 | 8/8 | 8/8 | 271 | 277 |
| 3 | 7/8 | 7/8 | 156 | 193 |
| **1** | **7/8** | **7/8** | **62** | 129 |

**Read — this is the headline.** With a reranker you trust, **top-1 holds 7/8
correctness on 62 chunk tokens**, versus 510 at top-10: an **~8× reduction in
tokens that ever arrive**, costing a single answer. That is the literal answer to
"why did 3,496 tokens arrive?" — because nothing upstream was tightening *k*.

### 6.3 FlashRank cold-start (20 candidates/call)

| phase | total ms | ms / pair | note |
|---|---|---|---|
| model construction | ~83 | — | one-time ONNX load |
| first user request (lazy init) | ~112 | 5.6 | construction + first inference |
| first inference (cold) | ~29 | 1.47 | graph not yet warm |
| warm inference (median) | ~29 | 1.43 | steady state |

**Read:** cold inference ≈ warm inference, so the only real cold cost is **model
construction (~83 ms)**. Construct the reranker at process startup, not on the
first user request, or that request eats the load.

---

## 7. Analysis

- **The bi-encoder isn't bad — the task is hard.** `all-MiniLM-L6-v2` is a solid
  retriever; it still scatters the gold chunk under adversarial near-twins. This
  is the realistic RAG failure mode: not "retrieval is broken" but "retrieval
  can't *order* look-alikes." Reranking is an ordering fix, not a recall fix.
- **gold-hit and correct moved together** here, which tells us the local model
  (`qwen3:8b`) reliably uses a correct chunk once it's in the window — the
  bottleneck was retrieval, not generation. On a weaker model the two would
  diverge, and the split metrics would show it.
- **Reranking and compression target different waste.** Reranking removes *whole
  irrelevant chunks* (the over-fetch); SmartCrusher squeezes *structure* from the
  survivors. On this prose-heavy corpus SmartCrusher often no-ops (prose has
  little structural redundancy) — which is exactly why, in Part 4, the token story
  is carried by the **k-sweep**, not by a compression delta. Wire both layers and
  you pay for the fewest, smallest, most-relevant tokens.
- **Local ≠ low-quality.** The BGE column proves you don't trade residency for
  ordering quality; you trade *latency* (CPU, no GPU). For most agent workloads
  that's an acceptable, tunable cost.

---

## 8. Conclusions & recommendations

1. **Add a reranker before your compression layer.** It cuts the payload at the
   source; everything downstream (compression, the LLM's attention budget, cost)
   benefits.
2. **Default to a self-hosted neural cross-encoder** (e.g. `bge-reranker-v2-m3`)
   when data residency matters. You get Cohere-class ordering with zero egress.
   Reach for FlashRank when latency is tight and the corpus is less adversarial;
   reach for a hosted API only when off-prem is acceptable.
3. **Tune `k` empirically with the k-sweep, per corpus.** The right *k* is the
   smallest one where correctness still holds. Here that was ~3–5; yours will
   differ. Don't pick a defensive large *k* "to be safe" — that *is* the
   over-fetch.
4. **Construct rerankers at startup.** The cold cost is model load, and it should
   never land on a user request.

---

## 9. Limitations / threats to validity

- **Synthetic corpus.** Northbank is fictional and the distractors are
  template-generated. This makes scoring clean and the bi-encoder's failure
  reproducible, but real corpora are noisier; validate on yours before quoting
  these exact ratios.
- **8 queries.** Enough to show the effect, not a statistically powered eval.
  gold-hit/correct are integer-over-8; treat them as directional.
- **Single generation model.** Results may shift on a smaller/larger model;
  the gold-hit vs correct split is built precisely to surface that if it happens.
- **Latency is hardware-bound.** The cold-start and BGE numbers are CPU-specific
  (no GPU). Per-pair "<1 ms" claims from FlashRank's docs land at ~1.4 ms here —
  quote your own machine.
- **SmartCrusher mostly no-ops** on this prose corpus by design; the compression
  win is demonstrated in Part 3, not re-litigated here.

---

## 10. Reproduce

```bash
pip install -r requirements.txt          # CPU torch is fine
ollama pull qwen3:8b

# run as modules from the repo root
python -m projects.local_first_reranking_layer.run_abc --top-k 5 --save
python -m projects.local_first_reranking_layer.run_ksweep --reranker bge --save
python -m projects.local_first_reranking_layer.bench_coldstart

# optional off-prem contrast
pip install cohere && export COHERE_API_KEY=...   # adds Config D
```

Results persist to `results_abc.json` / `results_ksweep.json` (full token in/out,
mean gold rank, and per-config detail beyond the printed tables).
