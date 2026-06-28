"""
Session A — retrieve, reason, verify, extract, store.

Run this first. It drives the four-agent harness over one compliance query,
then writes the verified facts into Mem0 with full provenance metadata so a
later, unrelated session can find and trust them.

Pipeline:
    RetrieverAgent → ReasonerAgent (Qwen3, thinking on) → VerifierAgent
        → ExtractorAgent → Mem0.add(... provenance metadata ...)

The provenance metadata written here is the whole point: every fact carries the
session_id, the Langfuse trace id, and the Headroom CCR content id, so Session B
can prove where a remembered fact came from.
"""

import json
import uuid
from datetime import datetime, timezone

from config import AGENT_ID
from harness.agents import (
    ExtractorAgent,
    ReasonerAgent,
    RetrieverAgent,
    VerifierAgent,
)
from harness.mem0_config import build_mem0

# --- Configuration ---
SESSION_ID = str(uuid.uuid4())
QUERY = (
    "What is the capital buffer requirement for Category 2 institutions "
    "under the March 2026 OSFI update?"
)

# The numeric claim the verifier must find grounded in the source.
EXPECTED_VALUE = "2.5%"

# Langfuse trace id — from Langfuse if wired, else generated for the experiment.
LANGFUSE_TRACE_ID = f"trace_{SESSION_ID[:8]}"

RESULTS_PATH = "results_session.json"


def run_session_a() -> dict:
    print(f"Session A — ID: {SESSION_ID}")
    print(f"Query: {QUERY}\n")

    retriever = RetrieverAgent()
    reasoner = ReasonerAgent()
    verifier = VerifierAgent()
    extractor = ExtractorAgent()

    # 1. Retrieve (Part 5 corpus stand-in).
    chunk = retriever.retrieve(QUERY, top_k=1)[0]
    print(f"Retrieved: {chunk.source_document} chunk {chunk.chunk_id} (page {chunk.page})")

    # The CCR content id comes from Headroom in the full stack; for the
    # experiment we anchor it to the retrieved chunk id.
    ccr_content_id = chunk.chunk_id

    # 2. Reason (Qwen3 with thinking on).
    print("Reasoning (Qwen3, thinking on)...")
    finding = reasoner.reason(QUERY, chunk)

    # 3. Verify (EVALUATOR pattern — deterministic).
    verdict = verifier.verify(finding, expected_value=EXPECTED_VALUE)
    print(f"Verification: {verdict.status}  checks={verdict.checks}")

    # 4. Build the session transcript the extractor compresses. In the real
    #    harness this is the accumulated LangGraph state; here we assemble it
    #    from the agents' outputs so the compression ratio is measured on real
    #    session content, not a hand-written blob.
    session_content = "\n".join(
        [
            f"Query: {QUERY}",
            "",
            f"Retrieved chunk (top_k=1, BGE reranker):\n\"{chunk.text}\"",
            "",
            f"Reasoning trace:\n{finding.reasoning_trace or '(thinking suppressed)'}",
            "",
            f"Finding:\n{finding.answer}",
            "",
            f"Verification: {verdict.status} — checks {verdict.checks}",
            f"Source: {chunk.source_document}, chunk {chunk.chunk_id}, page {chunk.page}",
        ]
    )
    session_tokens = len(session_content.split())
    print(f"\nSession content: ~{session_tokens} tokens (approximate)")

    # 5. Extract durable facts (compression step).
    print("Extracting facts...")
    facts = extractor.extract(session_content)
    print(f"Extracted {len(facts)} facts")
    for f in facts:
        print(f"  → [{f['confidence']}] {f['fact']}")

    # 6. Write to Mem0 with provenance metadata.
    mem0 = build_mem0()
    stored_ids = []
    for fact in facts:
        # A verified harness finding is "high"; promote confidence accordingly.
        confidence = "high" if verdict.passed and fact.get("source_type") == "verified" \
            else fact["confidence"]
        result = mem0.add(
            messages=[{"role": "user", "content": fact["fact"]}],
            user_id=AGENT_ID,
            metadata={
                "session_id": SESSION_ID,
                "langfuse_trace_id": LANGFUSE_TRACE_ID,
                "ccr_content_id": ccr_content_id,
                "source_document": chunk.source_document,
                "guideline_ref": fact.get("guideline_ref", "") or chunk.guideline_ref,
                "confidence": confidence,
                "source_type": fact["source_type"],
                "verification_status": verdict.status,
                "stored_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        # Mem0 returns {"results": [{"id": ...}, ...]} on recent versions.
        if isinstance(result, dict) and result.get("results"):
            stored_ids.extend(r.get("id", "unknown") for r in result["results"])
        else:
            stored_ids.append(result.get("id", "unknown") if isinstance(result, dict) else "unknown")

    # 7. Save results for Part 7 citation.
    facts_count = max(len(facts), 1)
    results = {
        "session_id": SESSION_ID,
        "query": QUERY,
        "model": "qwen3:8b",
        "verification_status": verdict.status,
        "session_tokens_approx": session_tokens,
        "facts_extracted": len(facts),
        "compression_ratio": round(session_tokens / facts_count, 1),
        "facts": facts,
        "provenance": {
            "langfuse_trace_id": LANGFUSE_TRACE_ID,
            "ccr_content_id": ccr_content_id,
            "source_document": chunk.source_document,
        },
        "mem0_ids": stored_ids,
    }

    with open(RESULTS_PATH, "w") as f:
        json.dump({"session_a": results}, f, indent=2)

    print(f"\nSession A complete. {session_tokens} tokens → {len(facts)} facts stored.")
    print(f"Compression: {results['compression_ratio']}:1")
    print(f"Results saved to {RESULTS_PATH}")
    return results


if __name__ == "__main__":
    run_session_a()
