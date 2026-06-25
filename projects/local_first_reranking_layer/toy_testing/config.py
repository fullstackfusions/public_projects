"""
Model and runtime config for the Part 4 reranking experiment.

Everything here runs on CPU and downloads its weights once from HuggingFace,
then stays fully local. The only off-premises option is Cohere Rerank, which
is opt-in (needs COHERE_API_KEY) and exists purely to demonstrate the
data-residency boundary the post argues about — it is never required to run.

Pull a generation model first:
  ollama pull qwen3:8b        # reasoning model, the documented default (5.2 GB)
  ollama pull qwen2.5:7b      # faster non-reasoning fallback (4.7 GB)
"""

import os

OLLAMA_BASE_URL = "http://localhost:11434"

# ---------------------------------------------------------------------------
# Generation model (Ollama, local)
# ---------------------------------------------------------------------------
MODELS = {
    "qwen3-8b":  "qwen3:8b",     # reasoning model — default; we disable thinking
    "qwen-7b":   "qwen2.5:7b",   # faster, no reasoning trace
    "gemma-12b": "gemma3:12b",
}
MODEL = MODELS["qwen3-8b"]

# qwen3 emits <think>…</think> by default. For a benchmark we want the answer,
# not the reasoning trace: it pollutes substring scoring and inflates latency.
# "/no_think" switches qwen3 into non-thinking mode; harmless for other models.
DISABLE_THINKING = True

# ---------------------------------------------------------------------------
# First-stage retrieval (bi-encoder, CPU)
# ---------------------------------------------------------------------------
# A bi-encoder embeds query and documents independently and compares vectors.
# Fast and cheap, but it has no cross-attention between query and document —
# which is exactly why it over-fetches near-duplicates. That over-fetch is the
# "why did 3,496 tokens arrive in the first place?" question Part 4 answers.
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 80 MB, CPU, downloads once

# How many candidates the first stage hands to the reranker.
FIRST_STAGE_TOP_N = 20

# Default number of chunks kept AFTER reranking and fed to compression+generation.
FINAL_TOP_K = 5

# ---------------------------------------------------------------------------
# Rerankers (cross-encoders) — the variable under test
# ---------------------------------------------------------------------------
# A cross-encoder scores (query, document) jointly with full cross-attention.
# Far more accurate at ordering than a bi-encoder, too expensive to run over a
# whole corpus — so it only ever sees the first stage's top-N candidates.
#
# FlashRank  → tiny ONNX-quantized cross-encoder, pure CPU, deterministic.
# BGE        → neural cross-encoder, CPU, Cohere-class quality, Apache-2.0,
#              weights on your disk. This is the column that should win for an
#              on-prem / data-residency constraint.
# Cohere     → hosted API, off-premises. Opt-in contrast only.
FLASHRANK_MODEL = "ms-marco-MiniLM-L-12-v2"     # FlashRank's default
BGE_MODEL = "BAAI/bge-reranker-v2-m3"           # swap to bge-reranker-base for speed
COHERE_MODEL = "rerank-v3.5"
COHERE_API_KEY = os.environ.get("COHERE_API_KEY")  # None → Cohere config is skipped

# Which rerankers the A/B/C runner exercises, in order. "none" is the
# first-stage-only baseline (Config A). "cohere" is appended automatically
# only when COHERE_API_KEY is present.
RERANKERS = ["none", "flashrank", "bge"]

# ---------------------------------------------------------------------------
# Compression (Part 3 carry-over)
# ---------------------------------------------------------------------------
# SmartCrusher is Headroom's deterministic rule-based compressor. Here it runs
# AFTER reranking: reranking decides WHICH chunks arrive, SmartCrusher squeezes
# the survivors. The two layers compose — Part 4 sits upstream of Part 3.
SMARTCRUSHER_ENABLED = True

# ---------------------------------------------------------------------------
# Corpus shape (data-heavy on purpose)
# ---------------------------------------------------------------------------
# The distractor count is what makes reranking matter. With a handful of docs a
# bi-encoder looks fine; with hundreds of lexically-similar near-duplicates it
# drags junk into the window and only a cross-encoder reliably sorts it out.
N_DISTRACTORS = 240
CORPUS_SEED = 42

SYSTEM_PROMPT = (
    "You are Northbank's internal compliance and platform assistant. "
    "Answer the question using ONLY the retrieved context. "
    "Be precise, cite the specific number, system, or role, and keep the "
    "answer to one or two sentences. If the context does not contain the "
    "answer, say so."
)
