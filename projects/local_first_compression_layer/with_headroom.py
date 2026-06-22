"""
Compressed run: retrieve → compress → generate.
headroom compress() fires in the compress node before Ollama sees the messages.

Usage:
  python with_headroom.py
"""

import json
from projects.local_first_compression_layer.graph import run
from projects.local_first_compression_layer.config import MODEL


def main():
    print(f"[headroom] model={MODEL}  compression=ON")
    state = run(with_compression=True)

    result = {
        "run": "with_headroom",
        "model": MODEL,
        "compression_applied": state["compression_applied"],
        "raw_token_estimate": state["raw_token_estimate"],
        "send_token_estimate": state["send_token_estimate"],
        "tokens_saved": state["tokens_saved"],
        "compression_ratio": state["compression_ratio"],
        "transforms_applied": state["transforms_applied"],
        "prompt_tokens_ollama": state["prompt_tokens"],
        "completion_tokens_ollama": state["completion_tokens"],
        "inference_time_s": state["inference_time_s"],
        "answer_preview": state["answer"][:400] + ("..." if len(state["answer"]) > 400 else ""),
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
