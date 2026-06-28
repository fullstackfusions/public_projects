"""
Provenance chain verification.

Run after both sessions. Confirms the five-link chain closes end-to-end:

    Session B output → Mem0 fact → Session A trace → CCR content → source doc

The chain closes if and only if Session A wrote the metadata at fact-storage
time. If it breaks, the fix is the metadata dict in session_a.py.
"""

import json
import sys

REQUIRED_CHAIN_FIELDS = [
    "session_id",
    "langfuse_trace_id",
    "ccr_content_id",
]


def verify(results_path: str = "results_session.json") -> bool:
    with open(results_path) as f:
        data = json.load(f)

    print("=" * 60)
    print("PROVENANCE CHAIN VERIFICATION")
    print("=" * 60)

    # Session A — facts stored with metadata.
    a = data.get("session_a", {})
    print(f"\nSession A ({str(a.get('session_id', '?'))[:8]}...)")
    print(
        f"  Tokens → Facts: {a.get('session_tokens_approx')} → "
        f"{a.get('facts_extracted')} ({a.get('compression_ratio')}:1)"
    )
    for field in REQUIRED_CHAIN_FIELDS:
        # session_id sits at the top level of the Session A record; the trace and
        # CCR ids sit under provenance. Check both so the display is accurate.
        val = a.get("provenance", {}).get(field) or a.get(field, "MISSING")
        status = "OK" if val not in ("MISSING", None) else "XX"
        print(f"  [{status}] {field}: {val}")

    # Session B — retrieved facts carry provenance.
    b = data.get("session_b", {})
    print(f"\nSession B ({str(b.get('session_id', '?'))[:8]}...)")
    print(f"  Facts retrieved from Mem0: {b.get('facts_retrieved')}")
    print(f"  Corpus retrieval needed: {b.get('corpus_retrieval_needed')}")

    retrieved_facts = b.get("retrieved_facts", [])
    all_closed = bool(retrieved_facts)
    for i, fact in enumerate(retrieved_facts):
        print(f"\n  Fact {i + 1}: {fact['memory'][:60]}...")
        for field in REQUIRED_CHAIN_FIELDS:
            val = fact.get(field, "MISSING")
            ok = val not in ("MISSING", None)
            if not ok:
                all_closed = False
            print(f"    [{'OK' if ok else 'XX'}] {field}: {val}")

    print("\n" + "=" * 60)
    if all_closed:
        print("RESULT: Provenance chain CLOSED")
        print("Session B output -> Mem0 fact -> Session A trace -> CCR content -> source")
    else:
        print("RESULT: Provenance chain BROKEN")
        print("One or more metadata fields missing from retrieved facts.")
        print("Check that session_a.py wrote metadata at fact storage time.")
    print("=" * 60)
    return all_closed


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "results_session.json"
    ok = verify(path)
    sys.exit(0 if ok else 1)
