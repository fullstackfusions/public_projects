"""
Baseline run: retrieve → generate (no compression node).
Establishes raw token count and inference time as the before-numbers.

Usage:
  python baseline.py
"""

import json
from projects.local_first_compression_layer.graph import run
from projects.local_first_compression_layer.config import MODEL


def main():
    print(f"[baseline] model={MODEL}  compression=OFF")
    state = run(with_compression=False)

    result = {
        "run": "baseline",
        "model": MODEL,
        "compression_applied": state["compression_applied"],
        "raw_token_estimate": state["raw_token_estimate"],
        "send_token_estimate": state["send_token_estimate"],
        "prompt_tokens_ollama": state["prompt_tokens"],
        "completion_tokens_ollama": state["completion_tokens"],
        "inference_time_s": state["inference_time_s"],
        "answer_preview": state["answer"][:400] + ("..." if len(state["answer"]) > 400 else ""),
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
