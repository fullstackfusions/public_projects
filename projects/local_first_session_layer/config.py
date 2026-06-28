"""
Model and runtime config for Part 6 — the cross-session memory experiment.

This part runs on a *reasoning* model. The previous parts (1–5) defaulted to
qwen2.5:7b; here we move up to **Qwen3 8B**, which is a hybrid reasoning model:
it emits an internal <think>…</think> trace before its answer. The harness uses
that trace where reasoning helps (the Reasoner agent) and suppresses it where we
need clean, deterministic output (the fact extractor returning JSON).

Pull the models first:
  ollama pull qwen3:8b            # reasoning model — the agent brain
  ollama pull nomic-embed-text    # 768-dim embeddings for Mem0/pgvector
"""

import os
from dataclasses import dataclass

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Supported local reasoning-capable models — pick one that fits your RAM.
MODELS = {
    "qwen3-8b":    "qwen3:8b",        # 5.2 GB — reasoning, the recommended default here
    "qwen3-14b":   "qwen3:14b",       # 9.3 GB — same family, more headroom
    "qwen3-4b":    "qwen3:4b",        # 2.6 GB — fits smaller machines, weaker reasoning
    "deepseek-8b": "deepseek-r1:8b",  # 4.9 GB — alternative reasoning model
}

# Change this to whichever model you have pulled.
MODEL = os.getenv("SESSION_MODEL", MODELS["qwen3-8b"])

# Embedding model for Mem0's vector store. nomic-embed-text is 768-dim —
# this MUST match `embedding_model_dims` in mem0_config.py.
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
EMBED_DIMS = 768

# pgvector connection (Docker container from docker-compose.yml / Step 1).
PGVECTOR = {
    "host":     os.getenv("PGVECTOR_HOST", "localhost"),
    "port":     int(os.getenv("PGVECTOR_PORT", "5432")),
    "dbname":   os.getenv("PGVECTOR_DB", "mem0db"),
    "user":     os.getenv("PGVECTOR_USER", "mem0user"),
    "password": os.getenv("PGVECTOR_PASSWORD", "mem0pass"),
    "collection_name": "agent_facts",
}

# Stable identity for the agent across sessions. Mem0 partitions memories by
# user_id, so Session A and Session B share memory only because they share this.
AGENT_ID = os.getenv("AGENT_ID", "compliance-agent-v1")


@dataclass(frozen=True)
class ReasoningConfig:
    """Controls how the Qwen3 thinking trace is handled per call site."""
    # When True we let the model think (better reasoning, slower, noisier output).
    # When False we append /no_think so the model skips the <think> block and
    # returns directly — used for the JSON fact extractor where we need a clean parse.
    enable_thinking: bool = True
    temperature: float = 0.0


# The Reasoner agent thinks; the Extractor does not (it must emit parseable JSON).
REASONER_REASONING = ReasoningConfig(enable_thinking=True, temperature=0.0)
EXTRACTOR_REASONING = ReasoningConfig(enable_thinking=False, temperature=0.0)
