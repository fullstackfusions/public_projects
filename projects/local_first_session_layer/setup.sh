#!/usr/bin/env bash
# One-shot setup for Part 6. Idempotent — safe to re-run.
set -euo pipefail

cd "$(dirname "$0")"

echo "==> 1. Python deps"
pip install -r requirements.txt --break-system-packages

echo "==> 2. pgvector (Docker)"
docker compose up -d
echo "    waiting for pgvector to be healthy..."
until docker compose exec -T pgvector pg_isready -U mem0user -d mem0db >/dev/null 2>&1; do
  sleep 1
done
docker compose exec -T pgvector psql -U mem0user -d mem0db \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "==> 3. Ollama models (reasoning brain + embedder)"
ollama pull qwen3:8b
ollama pull nomic-embed-text

echo
echo "Setup complete. Run the experiment:"
echo "  python sessions/session_a.py   # retrieve + reason + verify + extract + store"
echo "  python sessions/session_b.py   # cross-session retrieval + answer"
echo "  python verify_provenance.py    # check the provenance chain closes"
