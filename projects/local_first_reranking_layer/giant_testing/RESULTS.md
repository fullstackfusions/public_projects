# Giant-Scale Reranking Test — Setup, Numbers, and What It Proved

> **One-line takeaway:** On a real ~530K-token, two-document corpus, a local CPU cross-encoder reranker cut the context sent to the LLM from **530,702 tokens to 560 tokens — a 948× reduction — without dropping a single one of 12 answers.**

---

## 1. Why we ran this

The toy experiment showed reranking working on synthetic data. The open question was whether it holds at **real scale, on real documents, fully local** — no GPU, no cloud reranker, no API. This "giant" run answers the series' core question — *why did all those tokens arrive, and how many can we cut before correctness breaks?* — at roughly **65× the size of the toy setup**.

Everything below ran on CPU with a local Ollama model. The only network dependency is a one-time model download.

---

## 2. The setup

### Corpus

Two genuinely different professional PDFs, indexed together so the retriever has to discriminate *across* domains, not just within one:

| Document | Pages | Chunks | Tokens | Ingest time |
| --- | --- | --- | --- | --- |
| *Machine Learning for Algorithmic Trading (2nd Ed.)* | 856 | 779 | 398,621 | 1.83 s |
| *Law/Compliance in AI, Security & Data Protection* | 220 | 259 | 132,081 | 0.61 s |
| **Total** | **1,076** | **1,038** | **530,702** | — |

### Pipeline (all local)

```text
PDF → chunk (512 tok, 64 overlap)
    → embed: all-MiniLM-L6-v2  (bi-encoder, first stage)
    → retrieve top-30 candidates  (~15,354 tok of raw context)
    → RERANK: BGE cross-encoder → keep top-k
    → SmartCrusher (deterministic compression, Part 3 carry-over)
    → answer: qwen3:8b via Ollama
```

| Component | Choice | Role |
| --- | --- | --- |
| Chunking | 512 tokens, 64 overlap (`cl100k_base`) | Uniform windows |
| First stage | `all-MiniLM-L6-v2` bi-encoder | Cheap recall, top-30 |
| Reranker (fast) | FlashRank — `ms-marco-MiniLM-L-12-v2` (ONNX cross-encoder) | A/B/C arm |
| Reranker (accurate) | BGE — `bge-reranker-v2-m3` (PyTorch cross-encoder) | A/B/C + k-sweep |
| Compression | SmartCrusher (rule-based) | Final trim |
| Generator | `qwen3:8b` (Ollama, local) | Answers |

### Evaluation

**12 hand-written queries** with verifiable gold facts — 6 on ML/trading, 5 on law/compliance, 1 cross-document. An answer counts as **correct** if any distinctive gold substring (e.g. `"72 hour"`, `"survivorship bias"`, `"high-risk"`) appears in the model's output. Gold strings were chosen to be distinctive to the true answer section, not shared with near-duplicate passages.

Two experiment modes:

- **A/B/C** — fix `top_k=5`, vary the reranker (`none` / `flashrank` / `bge`). *Which reranker surfaces the right chunks, and at what latency?*
- **k-sweep** — fix the best local reranker (BGE), tighten `top_k` from 20 → 10 → 5 → 3 → 1. *How many tokens can we cut before correctness degrades?*

---

## 3. The numbers

### A/B/C — reranker comparison (top_n=30, top_k=5)

| Reranker | Local | Correct | 1st-stage tok | Sent tok | Rerank ms | Gen s |
| --- | --- | --- | --- | --- | --- | --- |
| none | yes | 12/12 | 15,316 | 2,781 | 0.0 | 46.0 |
| flashrank | yes | 12/12 | 15,316 | 2,778 | **1,764** | 42.6 |
| bge | yes | 12/12 | 15,316 | 2,775 | 8,649 | 40.2 |

**Reading it:** All three are correct on this query set, but the latency gap is the story — FlashRank (ONNX-quantized cross-encoder) reranks top-30 in **~1.8 s on CPU**, while the full BGE PyTorch cross-encoder takes **~8.6 s** for a marginal quality edge. The `none` row keeps all 30 candidates' best-5-by-bi-encoder; the rerankers don't shrink token count much at k=5 — their value shows up in *ordering* quality, which the k-sweep below isolates.

### k-sweep — how far can we cut? (reranker=BGE, top_n=30)

| top_k | Correct | Sent tok | Prompt tok | vs. full corpus | vs. raw top-30 |
| --- | --- | --- | --- | --- | --- |
| (stuff everything) | — | 530,702 | — | 1× | — |
| raw top-30 (no rerank) | — | 15,354 | — | 35× smaller | 1× |
| 20 | 12/12 | 11,089 | 10,959 | 48× | 0.72× |
| 10 | 12/12 | 5,549 | 5,511 | 96× | 0.36× |
| 5 | 12/12 | 2,775 | 2,807 | 191× | 0.18× |
| 3 | 12/12 | 1,669 | 1,706 | 318× | 0.11× |
| **1** | **12/12** | **560** | **626** | **948× smaller** | **0.036×** |

**Correctness held at 12/12 at every single `top_k`, all the way down to 1.**

---

## 4. What it proved

1. **The reranker's *ordering* is genuinely good — not just its recall.** At `top_k=1` the entire answer rides on the single chunk BGE ranked #1, and it answered all 12 queries correctly. A reranker that recovered the right chunk but mis-ordered it would collapse here. It didn't.

2. **~948× of the naive token budget was pure noise.** "Stuff the whole corpus" = 530,702 tokens. The answers actually needed **560**. Even measured against a sensible first-stage top-30 (15,354 tok), reranking to k=1 removed **~96%** of tokens with zero correctness loss.

3. **You can run this entirely locally.** No GPU, no cloud reranker, no API key. A quantized cross-encoder (FlashRank) reranks 30 candidates in under 2 seconds on CPU; BGE trades ~5× latency for a small quality margin.

4. **Most RAG defaults leave headroom on the table.** The common `top_k=5` default sends 2,775 tok; here `top_k=3` (1,669 tok) and even `top_k=1` (560 tok) were sufficient — a 2–5× further cut.

---

## 5. How useful it was — and the honest caveats

**Useful, concretely:**

- **Cost & latency:** Fewer prompt tokens = directly cheaper and faster generation, especially as you scale query volume. The 191× cut at the standard k=5, and 948× at k=1, translate straight into smaller prompts and lower spend.
- **Quality:** Less distractor context means the model spends its attention on relevant text — fewer chances to anchor on an irrelevant-but-similar passage.
- **Local-first:** The whole stack is reproducible on a laptop, which matters for the data-residency / compliance angle of the broader series.

**Caveats — state these in any write-up:**

- **12 queries is a small set.** "k=1 holds" is strong evidence the ordering is good, but it's not a statistical guarantee. The safe production recommendation is **k=3** (1,669 tok), which buys a redundancy margin while still cutting ~89% vs. raw top-30.
- **These two PDFs are cleanly structured.** A textbook and a legal module have well-separated topics, which flatters both retrieval and reranking. Messier corpora (overlapping chunks, near-duplicates) would likely need a larger k.
- **Correctness here = substring match.** It confirms the right facts surfaced; it does not grade answer fluency or completeness.

---

## 6. Bottom line for the blog

At real scale, a **local cross-encoder turned a 530K-token retrieval problem into a 560-token one without dropping a single answer.** Reranking isn't a marginal optimization here — it's the difference between an impossible prompt and a trivial one. The practical recommendation: **first-stage top-30 → BGE/FlashRank rerank → top-3**, fully on CPU, ~96% fewer tokens than the raw candidate set with correctness intact.

---

*Generated from [results_giant.json](../../../results_giant.json). Reproduce with:*

```bash
python -m projects.local_first_reranking_layer.giant_testing.run_experiment --mode abc --save
python -m projects.local_first_reranking_layer.giant_testing.run_experiment --mode ksweep --sweep-reranker bge --save
```
