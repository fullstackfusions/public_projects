"""
Model and runtime config for the hands-on experiment.
Set MODEL to whichever you have pulled in Ollama.

Pull a model first:
  ollama pull qwen2.5:7b
  ollama pull deepseek-r1:8b
  ollama pull glm4:9b
"""

from dataclasses import dataclass

OLLAMA_BASE_URL = "http://localhost:11434"

# Supported local models — pick one that fits your RAM
MODELS = {
    "qwen-7b":      "qwen2.5:7b",       # 4.7 GB  — recommended default
    "qwen-14b":     "qwen2.5:14b",      # 9.0 GB
    "deepseek-8b":  "deepseek-r1:8b",   # 4.9 GB  — reasoning model
    "glm-9b":       "glm4:9b",          # 5.5 GB
}

# Change this to whichever model you have available
MODEL = MODELS["qwen-7b"]

# Headroom compression target ratio for prose (0.0–1.0, lower = more aggressive)
PROSE_RATIO = 0.4

USER_QUERY = (
    "Which platform team engineers have deploy permissions? "
    "Explain how headroom's compress() function routes content to the right compressor."
)

SYSTEM_PROMPT = (
    "You are a senior platform engineer assistant. "
    "Answer questions using the retrieved context. "
    "Be precise and cite specific details."
)
