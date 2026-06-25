# Giant-Scale Reranking Experiment

A real-world, **fully local** reranking benchmark over two large PDFs
(~530K tokens, 1,038 chunks). It answers one question at production scale:

> *Why did all those tokens arrive — and how many can we cut before correctness breaks?*

The pipeline retrieves with a cheap bi-encoder, reorders with a CPU
cross-encoder reranker, trims with a deterministic compressor, and answers
with a local Ollama model. No GPU, no cloud API.

See [RESULTS.md](./RESULTS.md) for the full write-up and numbers. Short version:
**530,702 → 560 tokens (948× cut) at 12/12 correct, down to `top_k=1`.**

---

## Pipeline

```text
PDF → chunk (512 tok, 64 overlap)
    → embed: all-MiniLM-L6-v2  (bi-encoder, first stage, top-30)
    → RERANK: FlashRank (ONNX) or BGE (PyTorch) cross-encoder → keep top-k
    → SmartCrusher (deterministic compression)
    → answer: qwen3:8b via Ollama
```

| Stage | Default | File |
| --- | --- | --- |
| Chunking | 512 tok / 64 overlap | [ingest.py](./ingest.py) |
| First-stage retrieval | `all-MiniLM-L6-v2` | [retrieval.py](./retrieval.py) |
| Reranking | `none` / `flashrank` / `bge` | [rerankers.py](./rerankers.py) |
| Compression | SmartCrusher | [compress.py](./compress.py) |
| Generation | `qwen3:8b` (Ollama) | [graph.py](./graph.py) |
| Eval queries | 12 verifiable Q&A | [eval_queries.py](./eval_queries.py) |
| Config | all knobs | [config.py](./config.py) |

---

## Prerequisites

1. **Python env** (repo uses conda). From the repo root:
   ```bash
   conda activate env311
   pip install -r projects/local_first_reranking_layer/toy_testing/requirements.txt
   ```
   Key deps: `sentence-transformers`, `flashrank`, `FlagEmbedding` (BGE),
   `tiktoken`, `pypdf`, `numpy`, `ollama`.

2. **Ollama** running locally with the generation model pulled:
   ```bash
   ollama serve            # if not already running
   ollama pull qwen3:8b
   ```
   > Generation is only needed for correctness scoring. Use `--no-generate`
   > to skip Ollama entirely and measure token scale in seconds.

3. **The two PDFs** must be present in [`data/`](./data/) (already included).

---

## Step 1 — Build the index (run once)

Chunk + embed both PDFs and persist to `index/` (gitignored artifacts):

```bash
python -m projects.local_first_reranking_layer.giant_testing.ingest
```

Re-embedding ~1,000 chunks takes a few seconds; subsequent runs load from
disk in milliseconds. Force a rebuild with `--force`.

---

## Step 2 — Run the experiments

All commands are run **from the repo root**.

### A/B/C — compare rerankers at a fixed `top_k`

Varies the reranker (`none` / `flashrank` / `bge`) so you can see which one
surfaces the right chunks and at what latency.

```bash
# Full run with generation + correctness (~15–20 min: 12 queries × 3 rerankers)
python -m projects.local_first_reranking_layer.giant_testing.run_experiment --mode abc --top-k 5 --save

# Fast, retrieval-only — shows token scale in seconds (no Ollama, no correctness)
python -m projects.local_first_reranking_layer.giant_testing.run_experiment --mode abc --no-generate
```

### k-sweep — how far can you cut `top_k`?

Fixes the reranker and tightens `top_k` from 20 → 10 → 5 → 3 → 1 to find the
token floor where correctness still holds.

```bash
python -m projects.local_first_reranking_layer.giant_testing.run_experiment --mode ksweep --sweep-reranker bge --save
```

### Both at once

```bash
python -m projects.local_first_reranking_layer.giant_testing.run_experiment --mode both --save
```

---

## CLI reference

| Flag | Default | Meaning |
| --- | --- | --- |
| `--mode {abc,ksweep,both}` | `both` | Which experiment to run |
| `--top-n` | `30` | First-stage candidate count |
| `--top-k` | `5` | Final kept chunks (abc mode) |
| `--sweep-reranker {none,flashrank,bge}` | `bge` | Reranker held fixed in k-sweep |
| `--no-generate` | off | Skip LLM; report tokens only (fast) |
| `--save` | off | Persist results to `results_giant.json` |

---

## Output

With `--save`, results are written to
[`results_giant.json`](./results_giant.json) **inside this folder**. Saving
**merges** with any existing file, so running `--mode abc --save` and
`--mode ksweep --save` in separate invocations keeps **both** blocks
(`abc` and `ksweep`) rather than overwriting.

The console also prints a formatted summary table per mode (see RESULTS.md
for an annotated example).

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Index not found` | Run the `ingest` step first |
| `HF_TOKEN` warning | Harmless — anonymous Hugging Face download; set `HF_TOKEN` to silence/speed up |
| Connection refused on generate | Start Ollama (`ollama serve`) and `ollama pull qwen3:8b`, or use `--no-generate` |
| Slow first run | First reranker call downloads the model; subsequent runs are cached |
