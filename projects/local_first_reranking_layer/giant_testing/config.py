"""
Config for the real-world PDF reranking experiment (giant_testing).

Two documents, ~1,030 real chunks, ~464K tokens total — roughly 65× larger
than the synthetic toy experiment.  Everything still runs on CPU; no GPU or
cloud API required (Cohere is opt-in for the residency-boundary contrast).
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
PDF_DIR   = _HERE / "data"
INDEX_DIR = _HERE / "index"           # created by ingest.py, gitignored
INDEX_DIR.mkdir(exist_ok=True)

CHUNKS_FILE     = INDEX_DIR / "chunks.json"
EMBEDDINGS_FILE = INDEX_DIR / "embeddings.npy"

# ---------------------------------------------------------------------------
# Ingestion / chunking
# ---------------------------------------------------------------------------
CHUNK_SIZE    = 512   # tokens per chunk (cl100k_base)
CHUNK_OVERLAP = 64    # tokens of overlap between consecutive chunks

# ---------------------------------------------------------------------------
# Retrieval — first stage (bi-encoder, CPU)
# ---------------------------------------------------------------------------
EMBED_MODEL      = "sentence-transformers/all-MiniLM-L6-v2"
FIRST_STAGE_TOP_N = 30   # more candidates than the toy (real docs need headroom)

# ---------------------------------------------------------------------------
# Reranking — second stage (cross-encoder, CPU)
# ---------------------------------------------------------------------------
FINAL_TOP_K    = 5
FLASHRANK_MODEL = "ms-marco-MiniLM-L-12-v2"
BGE_MODEL       = "BAAI/bge-reranker-v2-m3"
COHERE_MODEL    = "rerank-v3.5"
COHERE_API_KEY  = os.environ.get("COHERE_API_KEY")

# Configs the experiment runner exercises.
# "cohere" is appended automatically only when COHERE_API_KEY is present.
RERANKERS = ["none", "flashrank", "bge"]

# ---------------------------------------------------------------------------
# Compression (SmartCrusher, deterministic rule-based, Part 3 carry-over)
# ---------------------------------------------------------------------------
SMARTCRUSHER_ENABLED = True

# ---------------------------------------------------------------------------
# Generation model (Ollama, local)
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL  = "http://localhost:11434"
MODEL            = "qwen3:8b"
DISABLE_THINKING = True   # strip <think>…</think> via /no_think

SYSTEM_PROMPT = (
    "You are a research assistant with access to retrieved document excerpts. "
    "Answer the question using ONLY the retrieved context. "
    "Be specific: cite exact figures, names, or section titles where available. "
    "If the context does not contain enough information, say so clearly."
)

# ---------------------------------------------------------------------------
# Experiment sweep
# ---------------------------------------------------------------------------
K_SWEEP_VALUES = [20, 10, 5, 3, 1]   # top-k values for the k-sweep table
