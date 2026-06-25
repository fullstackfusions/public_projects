# Reranking vs. PageIndex: Two Architectures for the Same Question

> **The question both tools answer:** *Why did the wrong tokens arrive?*
> Reranking and PageIndex give fundamentally different answers — one filters noise after the fact, the other never retrieves the noise in the first place. Where PageIndex sits in this series is non-obvious, and the answer changes depending on which part you look at. This note maps it precisely.

---

## 1. First, what reranking actually is

Reranking in a Retrieval-Augmented Generation (RAG) pipeline is a **second-pass quality filter**. Your first-stage retriever casts a wide, cheap net and returns a list of *plausibly* relevant documents. The reranker then re-examines each candidate against the query in far greater depth and reorders them so the genuinely relevant passages rise to the top before they reach the LLM.

The distinction that matters is *how deeply* a model looks at the query–document pair:

| Stage | Model type | How it scores | Cost | Role |
| --- | --- | --- | --- | --- |
| **First-stage retrieval** | **Bi-encoder** | Encodes query and document *separately* into vectors, compares by cosine similarity | Cheap, pre-computable, sub-ms | Recall — cast a wide net |
| **Reranking** | **Cross-encoder** | Encodes query and document *together* in one forward pass; full token-level attention | Expensive, per-pair, can't be cached | Precision — sort the net's catch |
| **Reranking (fast)** | **ONNX-quantized cross-encoder** | Same architecture, INT8/quantized graph compiled for CPU | ~3–10× faster, slight accuracy give-back | Precision on commodity hardware |

A bi-encoder is fast precisely *because* it never lets the query and document interact — it just compares two pre-baked vectors. A cross-encoder is accurate precisely *because* it does the opposite: it reads the query and document jointly, so "Sharpe ratio" in the query can attend directly to "risk-adjusted return" in the passage. That joint attention is the whole point — and the whole cost. ONNX quantization (the path FlashRank takes) keeps the cross-encoder architecture but shrinks the numerics so it runs locally on a CPU in milliseconds instead of needing a GPU.

This series builds two local rerankers on exactly this spectrum:

- **FlashRank** — an ONNX-quantized cross-encoder. ~1.7s for top-30 on CPU in our giant-corpus test.
- **BGE reranker** — a full PyTorch cross-encoder. ~8.6s for the same work — ~5× slower, marginally higher ceiling.

Both do the same job: take ~30 noisy first-stage candidates, score them properly, keep the best 5, and hand a lean context to the LLM.

---

## 2. What PageIndex actually does (technically)

PageIndex ([VectifyAI/PageIndex](https://github.com/VectifyAI/PageIndex)) throws the entire pipeline above out and replaces it with something that looks more like how a human uses a table of contents.

**Standard RAG (what we built):**

```text
PDF → chunk into 512-token windows → embed → vector search → rerank → LLM
```

**PageIndex — "vectorless, reasoning-based RAG":**

```text
PDF → build a semantic tree (titles + one-line summaries + page refs, hierarchical)
   → at query time, an LLM agent traverses the tree by reasoning
   → navigates directly to the right section, like a human reading a contents page
   → returns only those pages to the LLM
```

There are **no vector embeddings, no similarity search, and no chunking**. The tree itself is tiny — just node titles, one-line summaries, and `start_index`/`end_index` page pointers — so the LLM can hold it in context, reason about *which branch answers this query*, and pull only the pages it decided are relevant.

The framing in their own words is sharp and worth keeping: **similarity ≠ relevance.** Vector RAG retrieves what is *similar*; what you actually want is what is *relevant*, and deciding relevance requires reasoning, not nearest-neighbour geometry. Inspired by AlphaGo-style tree search, PageIndex does retrieval in two steps:

1. Generate a "table-of-contents" tree index of the document.
2. Perform agentic, reasoning-based retrieval by searching that tree.

It reports **state-of-the-art 98.7% accuracy on FinanceBench** (via the Mafin 2.5 system built on it), a financial-document QA benchmark where vector RAG historically struggles — exactly the structured, professional-document regime it's designed for. (MIT-licensed, ~33k GitHub stars; self-host with standard PDF parsing, or use their cloud OCR/tree pipeline for higher-quality trees.)

---

## 3. Where it fits in the 6-part series

| Part | Boundary | Tool(s) you built | PageIndex relevance |
| --- | --- | --- | --- |
| 1 | Control flow | LangGraph | **Weak** — different problem (agent skipping steps) |
| 2 | Shell output | RTK | **None** — compresses command output, different domain |
| 3 | Content (in-session) | Headroom SmartCrusher | **Upstream fix** — see §5 |
| 4 | Retrieval quality | FlashRank, BGE | **Direct alternative** — same problem, different architecture |
| 5 | Session boundary | Mem0, Hermes | **None** — cross-session memory, unrelated |
| 6 | Audit boundary | CCR + Langfuse | **Meaningful complement** — see §6 |

The short version: PageIndex isn't a *seventh tool* you bolt onto the stack. It's an **alternative architecture for Part 4** that pays a different set of costs — and, almost as a side effect, it strengthens Parts 3 and 6.

---

## 4. Part 4 — the direct alternative

This is where PageIndex is most relevant. It solves *exactly* the problem your reranker solves — why did the wrong tokens arrive — but attacks it from the opposite end. Reranking lets the noise in and then filters it. PageIndex reasons about structure so the noise is never retrieved.

```text
Your approach (reranking):            PageIndex approach:
retrieve 30 noisy candidates          navigate the tree by reasoning
  ↓                                     ↓
cross-encoder filters to top 5        lands on the 2 pages that answer it
  ↓                                     ↓
send ~2,780 tokens to LLM             send ~1,024 tokens to LLM
```

The tradeoff is real and worth stating plainly:

| | **Reranking (your build)** | **PageIndex** |
| --- | --- | --- |
| **Works on** | Any text, structured or not | Well-structured documents (books, legal, financial) |
| **Retrieval mechanism** | Embedding + cross-encoder inference | LLM call that traverses a tree |
| **Retrieval cost** | Milliseconds, no LLM call | One+ LLM call per query (tree traversal) |
| **Accuracy ceiling** | Capped by first-stage recall | Higher on professional docs (98.7% FinanceBench) |
| **Auditability** | "chunk from page 145" | "navigated Section 3.2 because the query asked about X" |
| **Fails when** | Corpus has no structure | Document has no clear hierarchy / query spans many sections |

The accuracy-ceiling row is the crux. A reranker can only ever reorder what the **first stage already retrieved** — if the bi-encoder's top-30 missed the one page that actually answers the query, no cross-encoder can recover it. PageIndex has no first-stage recall ceiling; it reasons over the *whole* document structure every time. The price is an LLM call per retrieval instead of a cached vector lookup.

For our two specific PDFs — an ML textbook with clean chapters and a law/compliance module with numbered sections — PageIndex would likely **outperform** the bi-encoder + reranker, because both documents have exactly the hierarchy it exploits.

---

## 5. Part 3 — an upstream fix for compression

The reason Part 3 needed SmartCrusher to compress ~3,496 tokens is that ~3,496 tokens arrived in the first place. Part 4 (reranking) already cuts that to ~2,780. PageIndex can cut it further still: if tree navigation lands on the exact 2-page section, you might hand the LLM ~800 tokens, making the SmartCrusher pass almost decorative.

```text
Series stack with PageIndex inserted:

query → PageIndex tree traversal → ~800 tokens (the right section)
                                      ↓
                                 SmartCrusher (light pass)
                                      ↓
                                   ~750 tokens → LLM
```

This is the general lesson of the whole series in miniature: **fixing a problem upstream makes every downstream fix less load-bearing.** Better retrieval doesn't just save tokens — it relieves pressure on compression, on context limits, and on the model's ability to ignore distractors.

---

## 6. Part 6 — a meaningful complement for audit

Part 6 asks a production question: *can I prove what the agent read on call #4712?*

A reranker can tell you *what* it sent — "chunk from page 145." PageIndex tells you *what and why*: "I navigated to Section 4.2 because the query asked about data-breach notification timelines, and the summary of Section 4.2 referenced GDPR Article 33." That is a **reasoning trace attached to retrieval**, and it is exactly the artifact a compliance audit wants.

Combined with Langfuse (Part 6), you'd capture the full chain: **which section, why it was selected, and what the model ultimately said** — all traceable, all explainable. That's the difference between "trust the vector search" and "here is the documented reasoning path."

---

## 7. The honest positioning

PageIndex is not a tool you'd *add* to the existing six-part stack. It's an **alternative architecture for Part 4** that trades costs differently:

- **Use reranking (your build)** when the corpus is unstructured, mixed, or latency-critical — heterogeneous text like web pages, chat logs, support tickets, or code. It needs no LLM call at retrieval time and runs in milliseconds locally.
- **Use PageIndex** when the corpus is professional, structured documents — legal, financial, compliance, technical manuals. You buy higher accuracy and genuine auditability, and you pay with an LLM call per retrieval.

For the **Northbank compliance-AI narrative**, PageIndex is arguably the *stronger* architectural choice, and the honest framing for the blog is this:

> Reranking is the **general-purpose** fix for retrieval quality. PageIndex is the **specialist** — the right tool when your documents have structure worth exploiting. The 98.7% FinanceBench result suggests it earns that specialization on precisely the document types Northbank holds: filings, contracts, and regulatory text with a hierarchy a model can reason over.

Two architectures, one question. The reranker filters noise after the fact; PageIndex refuses to retrieve it. Which one is "right" is entirely a function of whether your documents have a structure worth reading like a human would.

---

### References

- PageIndex — *Vectorless, Reasoning-based RAG* — <https://github.com/VectifyAI/PageIndex>
- Mafin 2.5 on FinanceBench (98.7%) — <https://github.com/VectifyAI/Mafin2.5-FinanceBench>
- FinanceBench dataset — <https://arxiv.org/abs/2311.11944>
- FlashRank (ONNX cross-encoder reranking) and BGE reranker — Part 4 of this series
