#!/usr/bin/env bash
set -euo pipefail

echo "=== RTK Token Killer — Setup ==="
echo ""

# Install RTK
if command -v rtk &>/dev/null; then
    echo "✓ RTK already installed: $(rtk --version)"
else
    echo "Installing RTK..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install rtk
    else
        curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
    fi
    echo "✓ RTK installed"
fi

# Install Python deps
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "✓ Python dependencies installed"

# Verify Ollama + Qwen2.5:7b
echo ""
if command -v ollama &>/dev/null; then
    if ollama list 2>/dev/null | grep -q "qwen2.5:7b"; then
        echo "✓ Ollama Qwen2.5:7b ready"
    else
        echo "Pulling Qwen2.5:7b model (this may take a few minutes)..."
        ollama pull qwen2.5:7b
        echo "✓ Qwen2.5:7b pulled"
    fi
else
    echo "⚠  Ollama not found — install from https://ollama.com, then: ollama pull qwen2.5:7b"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Commands:"
echo "  python main.py benchmark       # measure token savings (no LLM)"
echo "  python main.py agent           # run LangGraph agent demo"
echo "  python main.py demo            # benchmark + agent"
