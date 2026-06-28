"""
Session B — cross-session retrieval.

Run this AFTER session_a.py. A fresh context, a differently-phrased query on the
same topic. It retrieves facts from Mem0 (not from the 530K corpus), injects
procedural + declarative memory, and answers. Then it checks the provenance
chain closes on every retrieved fact.

The query deliberately swaps vocabulary ("Tier 2" for "Category 2") to test
whether the embedding model closes the gap — that's Q1 of the three questions
Part 7 answers.
"""

import json
import uuid

from config import AGENT_ID, REASONER_REASONING
from harness.mem0_config import build_mem0
from harness.prompt_builder import build_system_prompt, inject_declarative_memory
from harness.reasoning import chat

SESSION_B_ID = str(uuid.uuid4())

# Different phrasing than Session A — tests semantic retrieval.
QUERY_B = (
    "What capital buffer percentage applies to Tier 2 institutions "
    "per recent OSFI guidance?"
)

RESULTS_PATH = "results_session.json"


def _meta(record: dict) -> dict:
    """Mem0 search records put provenance under 'metadata'."""
    return record.get("metadata", {}) or {}


def run_session_b() -> dict:
    print(f"Session B — ID: {SESSION_B_ID}")
    print(f"Query: {QUERY_B}\n")

    # 1. Retrieve relevant facts from Mem0.
    mem0 = build_mem0()
    search = mem0.search(query=QUERY_B, user_id=AGENT_ID, limit=3)
    # Recent Mem0 wraps hits in {"results": [...]}.
    retrieved = search["results"] if isinstance(search, dict) else search

    print(f"Retrieved {len(retrieved)} facts from Session A memory:")
    for r in retrieved:
        m = _meta(r)
        print(f"  → {r['memory']}")
        print(f"     source_session: {m.get('session_id', 'MISSING')}")
        print(f"     langfuse_trace: {m.get('langfuse_trace_id', 'MISSING')}")
        print(f"     ccr_content_id: {m.get('ccr_content_id', 'MISSING')}")

    # 2. Build prompt: procedural (deterministic) + declarative (probabilistic).
    base_prompt = f"Answer this compliance query accurately: {QUERY_B}"
    system_with_skills = build_system_prompt(base_prompt)
    system_with_memory = inject_declarative_memory(system_with_skills, retrieved)

    # 3. Run inference — Qwen3 reasons over remembered facts, no corpus retrieval.
    reply = chat(system_with_memory, cfg=REASONER_REASONING)
    answer = reply.answer
    print(f"\nSession B answer:\n{answer}")

    # 4. Check provenance chain closure on every retrieved fact.
    chain_closed = bool(retrieved) and all(
        _meta(r).get("session_id")
        and _meta(r).get("langfuse_trace_id")
        and _meta(r).get("ccr_content_id")
        for r in retrieved
    )
    print(f"\nProvenance chain closed: {chain_closed}")

    # 5. Append to results.
    session_b_results = {
        "session_id": SESSION_B_ID,
        "query": QUERY_B,
        "model": "qwen3:8b",
        "facts_retrieved": len(retrieved),
        "retrieved_facts": [
            {
                "memory": r["memory"],
                "session_id": _meta(r).get("session_id"),
                "langfuse_trace_id": _meta(r).get("langfuse_trace_id"),
                "ccr_content_id": _meta(r).get("ccr_content_id"),
            }
            for r in retrieved
        ],
        "answer": answer,
        "reasoning_trace": reply.reasoning,
        "provenance_chain_closed": chain_closed,
        "corpus_retrieval_needed": False,  # memory substituted
    }

    with open(RESULTS_PATH, "r+") as f:
        data = json.load(f)
        data["session_b"] = session_b_results
        f.seek(0)
        f.truncate()
        json.dump(data, f, indent=2)

    return session_b_results


if __name__ == "__main__":
    run_session_b()
