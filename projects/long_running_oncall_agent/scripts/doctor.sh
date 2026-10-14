#!/usr/bin/env bash
# Preflight checks for running the stack locally. Prints what to fix; changes nothing.
set -u
ok()   { printf '  \033[32mok\033[0m    %s\n' "$1"; }
warn() { printf '  \033[33mwarn\033[0m  %s\n' "$1"; }
fail() { printf '  \033[31mfail\033[0m  %s\n' "$1"; FAILED=1; }
FAILED=0
cd "$(dirname "$0")/.."

echo "Docker"
if ! docker info >/dev/null 2>&1; then
  fail "Docker is not running. Start Docker Desktop."
else
  mem=$(docker info --format '{{.MemTotal}}')
  gb=$(awk -v m="$mem" 'BEGIN{printf "%.1f", m/1e9}')
  if awk -v m="$mem" 'BEGIN{exit !(m >= 15e9)}'; then ok "Docker memory ${gb} GB (enough for 'make up')"
  else warn "Docker memory ${gb} GB: use 'make up-lite' (16k ctx, 1 worker), or raise to 16 GB in Docker Desktop > Settings > Resources for 'make up'"; fi
fi

echo ".env"
if [ ! -f .env ]; then
  fail ".env missing: run 'make env', then add SCALEDOWN_API_KEY"
else
  grep -qE '^SCALEDOWN_API_KEY=.+' .env && ok "SCALEDOWN_API_KEY set" \
    || fail "SCALEDOWN_API_KEY empty in .env (needed by scaledown* profiles)"
  grep -qE '^(OPENAI_API_KEY|OPEN_AI_API_KEY)=.+' .env && ok "OpenAI key set (frontier bench only)" \
    || warn "no OpenAI key: only 'make frontier' needs it"
fi

echo "Models"
models="${OLLAMA_MODELS_DIR:-$HOME/.ollama/models}"
if [ -d "$models/manifests/registry.ollama.ai/library/qwen3" ]; then
  ok "qwen3 found in $models (reused, no download)"
else
  warn "no cached qwen3 in $models: first 'make up' downloads ~6.6 GB (qwen3:8b + qwen3:1.7b)"
fi

echo "Ports"
for port in 8000 8100 "${OLLAMA_HOST_PORT:-11435}"; do
  owner=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | awk 'NR==2{print $1}')
  if [ -z "$owner" ]; then ok "port $port free"
  elif [[ "$owner" == com.docke* || "$owner" == docker* ]]; then ok "port $port held by Docker (this stack already up?)"
  else fail "port $port is used by '$owner': stop it or change the port mapping"; fi
done

echo "Host Ollama (optional, for 'make up-metal')"
owner=$(lsof -nP -iTCP:11434 -sTCP:LISTEN 2>/dev/null | awk 'NR==2{print $1}')
if [[ "$owner" == ollama* || "$owner" == Ollama* ]]; then ok "native Ollama answering on :11434"
elif [ -n "$owner" ]; then warn ":11434 is held by '$owner' (an older version of this stack? run 'make down && make up'), not a native Ollama"
else warn "no native Ollama on :11434: fine unless you want 'make up-metal'"; fi

[ "$FAILED" = 0 ] && echo "Ready." || { echo "Fix the failures above first."; exit 1; }
