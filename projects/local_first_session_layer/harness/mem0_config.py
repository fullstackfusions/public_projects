"""
Mem0 pointed at local pgvector + local Ollama.

Same local-first principle as the rest of the stack: the vector store is a
Docker pgvector container, the LLM Mem0 uses to deduplicate/merge facts is the
local Qwen3, and the embedder is local nomic-embed-text. Nothing leaves the box.

Note on the Mem0 LLM: Mem0 runs its own internal "should I add/update/merge this
memory?" reasoning step using the configured LLM. We pass `qwen3:8b` there too.
Qwen3 will emit <think> blocks; recent Mem0 + Ollama handle that, but if you see
JSON-parse errors from Mem0's internal step, set the Mem0 LLM model to a
non-reasoning model (e.g. qwen2.5:7b) — the agent brain stays qwen3:8b regardless.
"""

from mem0 import Memory

from config import (
    AGENT_ID,
    EMBED_DIMS,
    EMBED_MODEL,
    MODEL,
    OLLAMA_BASE_URL,
    PGVECTOR,
)


def build_mem0() -> Memory:
    config = {
        "vector_store": {
            "provider": "pgvector",
            "config": {
                "host": PGVECTOR["host"],
                "port": PGVECTOR["port"],
                "dbname": PGVECTOR["dbname"],
                "user": PGVECTOR["user"],
                "password": PGVECTOR["password"],
                "collection_name": PGVECTOR["collection_name"],
                "embedding_model_dims": EMBED_DIMS,  # must match the embedder below
            },
        },
        "llm": {
            "provider": "ollama",
            "config": {
                "model": MODEL,
                "temperature": 0,
                "ollama_base_url": OLLAMA_BASE_URL,
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": EMBED_MODEL,
                "ollama_base_url": OLLAMA_BASE_URL,
            },
        },
    }
    return Memory.from_config(config)


# Convenience re-export so sessions can `from harness.mem0_config import AGENT_ID`.
__all__ = ["build_mem0", "AGENT_ID"]
