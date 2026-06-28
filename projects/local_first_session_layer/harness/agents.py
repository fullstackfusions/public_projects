"""
The session harness — a small multi-agent pipeline.

The guide frames Session A as "retrieve → reason → verify → extract". That is a
multi-agent harness, so we build it as one instead of a single straight-line
script. Four roles, each with a narrow job:

    RetrieverAgent  — pulls the relevant chunk(s) for a query (Part 5 corpus)
    ReasonerAgent   — Qwen3 *with thinking on* — works out the finding
    VerifierAgent   — the EVALUATOR pattern from Part 1: checks the finding
                      against the retrieved source and the procedural rules
    ExtractorAgent  — compresses the verified session into durable facts

The harness is deliberately model-light on the deterministic edges (retrieval,
verification rules) and model-heavy only where judgement is needed (reasoning).
That mirrors the whole stack's thesis: deterministic where you can be,
probabilistic only where you must.

For the experiment the RetrieverAgent serves a small in-repo corpus so the demo
runs without re-indexing the 530K-token Part 5 PDF set. To wire it to the real
reranker, replace `RetrieverAgent.retrieve` with a call into
local_first_reranking_layer's retrieval/rerank pipeline — the rest is unchanged.
"""

from dataclasses import dataclass, field

from config import REASONER_REASONING
from harness.fact_extractor import extract_facts
from harness.prompt_builder import build_system_prompt
from harness.reasoning import chat


# --------------------------------------------------------------------------- #
# Retrieval
# --------------------------------------------------------------------------- #

@dataclass
class RetrievedChunk:
    text: str
    source_document: str
    chunk_id: str
    page: int
    guideline_ref: str


# Stand-in for the Part 5 reranker's top_k output. In the real stack these come
# from BGE rerank over the OSFI corpus; here they're a faithful sample so the
# provenance chain has real ids to carry.
_CORPUS: list[RetrievedChunk] = [
    RetrievedChunk(
        text=(
            "OSFI Guideline B-20, March 2026 revision, Section 4.1: Capital buffer "
            "requirements for Category 2 institutions are increased to 2.5% of "
            "risk-weighted assets, effective Q2 2026. This supersedes the previous "
            "requirement of 2.0% established in the 2023 revision. Institutions must "
            "demonstrate compliance by June 30, 2026."
        ),
        source_document="osfi_b20_2026.pdf",
        chunk_id="chunk_247_osfi_b20_2026",
        page=34,
        guideline_ref="OSFI-B20-v3.2 clause 4.1",
    ),
]


class RetrieverAgent:
    """Selects the most relevant chunk(s) for a query."""

    def retrieve(self, query: str, top_k: int = 1) -> list[RetrievedChunk]:
        # The toy corpus has a single authoritative chunk; a real reranker would
        # score and slice here. Kept trivial on purpose — retrieval quality is
        # Part 5's job, this part is about what happens to the chunk afterward.
        return _CORPUS[:top_k]


# --------------------------------------------------------------------------- #
# Reasoning  (Qwen3 with thinking ON)
# --------------------------------------------------------------------------- #

@dataclass
class Finding:
    answer: str
    reasoning_trace: str
    grounded_in: RetrievedChunk


class ReasonerAgent:
    """Qwen3 reasons over the retrieved chunk to produce a compliance finding."""

    def reason(self, query: str, chunk: RetrievedChunk) -> Finding:
        system = build_system_prompt(
            "You are a compliance analyst. Answer ONLY from the provided source. "
            "Follow the procedural output structure exactly."
        )
        prompt = (
            f"Query: {query}\n\n"
            f"Source ({chunk.source_document}, page {chunk.page}, "
            f"{chunk.guideline_ref}):\n\"{chunk.text}\"\n\n"
            "Produce the compliance finding."
        )
        reply = chat(prompt, cfg=REASONER_REASONING, system=system)
        return Finding(
            answer=reply.answer,
            reasoning_trace=reply.reasoning,  # Qwen3's <think> trace, kept for provenance
            grounded_in=chunk,
        )


# --------------------------------------------------------------------------- #
# Verification  (the EVALUATOR pattern from Part 1)
# --------------------------------------------------------------------------- #

@dataclass
class Verdict:
    status: str            # VERIFIED | UNVERIFIED | REQUIRES_HUMAN_REVIEW
    checks: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == "VERIFIED"


class VerifierAgent:
    """
    Deterministic check that the finding is grounded and rule-compliant.

    No model call here on purpose: verification is the harness's job, and the
    harness is where we want determinism. We assert the finding cites its source
    and that any numeric claim actually appears in the retrieved chunk.
    """

    def verify(self, finding: Finding, expected_value: str | None = None) -> Verdict:
        chunk = finding.grounded_in
        answer = finding.answer

        checks = {
            "cites_source_document": chunk.source_document.lower() in answer.lower()
            or chunk.guideline_ref.split()[0].lower() in answer.lower(),
            "value_grounded_in_source": (
                expected_value is None
                or (expected_value in answer and expected_value in chunk.text)
            ),
            "has_guideline_ref": bool(chunk.guideline_ref),
        }

        if all(checks.values()):
            status = "VERIFIED"
        elif not checks["value_grounded_in_source"]:
            status = "REQUIRES_HUMAN_REVIEW"
        else:
            status = "UNVERIFIED"

        return Verdict(status=status, checks=checks)


# --------------------------------------------------------------------------- #
# Extraction  (compression at session close)
# --------------------------------------------------------------------------- #

class ExtractorAgent:
    """Thin wrapper so the harness reads as four named agents, not three + a func."""

    def extract(self, session_content: str) -> list[dict]:
        return extract_facts(session_content)
