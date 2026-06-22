# Headroom — Local Compression Layer Hands-on

LangGraph + LangChain + local Ollama models (Qwen / DeepSeek / GLM) with Headroom as a compression node in the pipeline.

**Research context:** [research-headroom.md](./research-headroom.md) | [perspective.md](./perspective.md)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   LangGraph pipeline                 │
│                                                     │
│  retrieve ──► [compress] ──► generate               │
│     │             │              │                   │
│  build RAG    headroom       ChatOllama             │
│  messages     compress()     (local model)           │
└─────────────────────────────────────────────────────┘
```

Two compiled graphs:
- **baseline_graph** — `retrieve → generate` (raw messages, no compression)
- **compressed_graph** — `retrieve → compress → generate` (headroom fires in the compress node)

The compress node converts LangChain messages to OpenAI-wire format, calls `headroom.compress()`, then passes the result to Ollama. Token counts come from Ollama's response metadata (`prompt_eval_count`); pre-send estimates use tiktoken cl100k_base.

---

## Why local models make compression MORE interesting

With cloud APIs the win is cost. With local 4B–14B models the win is **context window pressure**:
- Qwen2.5:7b — 32k context window
- DeepSeek-R1:8b — 128k but slow on CPU, effective window is often smaller
- GLM-4:9b — 128k

A bloated RAG payload that's 3k tokens raw becomes 800 tokens after compression. That's the difference between fitting in context and not, and the difference between fast inference and slow.

---

## Setup

### 1. Install Ollama and pull a model

```bash
# Install Ollama: https://ollama.com
ollama pull qwen2.5:7b        # recommended default (4.7 GB)
# ollama pull deepseek-r1:8b  # reasoning model (4.9 GB)
# ollama pull glm4:9b         # GLM-4 (5.5 GB)
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Pick your model (optional)

Edit [config.py](headroom/config.py) — change `MODEL` to whichever model you pulled.

---

## Run

### Baseline only (no compression)

```bash
python baseline.py
```

Outputs raw token estimate + Ollama-reported prompt tokens + inference time.

### Compressed run only

```bash
python with_headroom.py
```

Same pipeline with the `compress` node wired in. Shows `compression_pct`.

### Full comparison table

```bash
python compare.py --save
```

Runs both back-to-back, prints a Rich table with delta percentages, saves `results.json`.

```bash
python compare.py --baseline-only   # skip headroom, useful if not installed yet
```

---

## What to watch

| Metric | What it tells you |
|---|---|
| `send_token_estimate` delta | How much headroom trimmed the payload (tiktoken approx) |
| `prompt_tokens_ollama` delta | Actual tokens the model processed (Ollama-reported) |
| `inference_time_s` delta | Wall-clock speedup from shorter context |
| Answer quality | Read both answers — does the compressed run still correctly list the engineers and explain the routing logic? |

The CacheAligner question doesn't apply to local models (no KV-cache billing), so the only failure mode is **semantic loss**: compressed answer misses facts from the original payload.

---

## Files

```
headroom/
  config.py                 model selection, Ollama URL, query
  graph.py                  LangGraph state + nodes + graph builders
  baseline.py               entry point: run without compression
  with_headroom.py          entry point: run with compress node
  compare.py                orchestrate both, print diff table
  data/
    sample_rag_chunks.py    RAG payload (JSON + code search + prose)
  requirements.txt
  README.md
```

---

## Extending

- **Swap in your own RAG data** — replace `sample_rag_chunks.py` with real retrieval output from pgvector or any document store.
- **Add a retrieval tool node** — wire a `headroom_retrieve` tool into the graph so the model can pull the original when the compressed version is insufficient.
- **Multi-turn conversation** — add an `AgentState["history"]` field and run multiple turns; watch whether compression compounds across turns.
