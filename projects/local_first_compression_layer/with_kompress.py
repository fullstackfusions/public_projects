"""
Compressed run WITH Kompress: retrieve → compress → generate.
Same pipeline as with_headroom.py, but the compress node also runs Kompress —
Headroom's HuggingFace extractive prose compressor — on the prose blocks.

This is the opt-in escalation: more reduction, but the ML model is
non-deterministic, so the exact compressed input is no longer guaranteed
reproducible across runs.

Usage:
  python with_kompress.py
"""

import argparse
import json
import sys
from pathlib import Path

from projects.local_first_compression_layer.graph import run
from projects.local_first_compression_layer.config import MODEL, KOMPRESS_MODEL


def main(out: str | None = None):
    print(f"[kompress] model={MODEL}  compression=ON  kompress={KOMPRESS_MODEL}", file=sys.stderr)
    state = run(with_compression=True, kompress=True)

    result = {
        "run": "with_kompress",
        "model": MODEL,
        "kompress_model": KOMPRESS_MODEL,
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
    if out:
        Path(out).write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", help="write the result JSON to this path")
    main(p.parse_args().out)
