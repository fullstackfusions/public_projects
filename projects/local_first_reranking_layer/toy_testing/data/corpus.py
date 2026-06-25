"""
A data-heavy, RAG-realistic corpus for the Part 4 reranking experiment.

The point of Part 4 is to answer: *why did 3,496 tokens arrive in the first
place?* The answer is that a bi-encoder first stage over-fetches. To show that
honestly you need a corpus where the right answer is one chunk hiding among
HUNDREDS of lexically near-identical distractors — not a 10-record toy.

So this module is:
  • GOLD_CHUNKS  — a handful of authoritative policy snippets, each holding the
    one correct fact for one evaluation query.
  • generate_distractors() — hundreds of realistic, deterministically-generated
    policy snippets that talk about the SAME topics (retention, encryption,
    breach SLAs, RPO, residency, MFA, incident SLAs) with DIFFERENT specifics.
    These are what a bi-encoder happily drags into the context window.
  • EVAL_QUERIES — questions whose correct answer is a distinctive token that
    appears in exactly one gold chunk.

Everything is fictional ("Northbank"), so the gold facts are defined by this
corpus, not by real regulation — which keeps correctness scoring deterministic.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Doc:
    id: str
    text: str
    kind: str = "prose"          # prose | json | gold
    topic: str = ""


@dataclass
class Query:
    id: str
    question: str
    gold: list[str]              # answer is correct if it contains any of these
    gold_doc_id: str
    topic: str = ""
    notes: str = ""


# ---------------------------------------------------------------------------
# GOLD — one authoritative chunk per query. These carry the only correct facts.
# ---------------------------------------------------------------------------

# Gold chunks are deliberately written WITHOUT keyword reinforcement. Each is a
# single natural policy statement. The distractors below are near-twins that
# share the same head noun phrase ("customer transaction records retained for…")
# and differ only in one qualifier ("completed" vs "pending") and the value.
# That overlap is what defeats a bi-encoder and forces a cross-encoder to earn
# its place — the whole argument of Part 4.

GOLD_CHUNKS: list[Doc] = [
    Doc("gold-retention-txn", kind="gold", topic="retention", text=(
        "Records Retention Standard, Section 4.2. Completed customer transaction "
        "records must be retained for 7 years from the settlement date before "
        "secure destruction.")),
    Doc("gold-encrypt-rest", kind="gold", topic="encryption", text=(
        "Cryptographic Standards, Section 2.1. Customer data at rest in primary "
        "production data stores must be encrypted using AES-256 with HSM-backed "
        "key management.")),
    Doc("gold-breach-sla", kind="gold", topic="breach", text=(
        "Privacy Breach Response, Section 6.4. Once a breach of customer personal "
        "information is confirmed, the primary privacy regulator must be notified "
        "within 72 hours of that confirmation.")),
    Doc("gold-approver-processor", kind="gold", topic="approval", text=(
        "Third-Party Risk Standard, Section 3.3. A new third-party data processor "
        "handling customer personal information may be engaged only after written "
        "approval by the Chief Privacy Officer.")),
    Doc("gold-rpo-core", kind="gold", topic="rpo", text=(
        "Business Continuity Plan, Section 5.1. The core banking database, the "
        "system of record for account balances, carries a Recovery Point Objective "
        "(RPO) of 15 minutes via continuous log shipping.")),
    Doc("gold-residency-pii", kind="gold", topic="residency", text=(
        "Data Residency Policy, Section 1.2. Canadian customer personal information "
        "must be stored and processed only in the Toronto and Montreal data centres "
        "and must not leave Canada.")),
    Doc("gold-mfa-prod", kind="gold", topic="mfa", text=(
        "Access Control Standard, Section 7.2. Human access to production systems "
        "holding customer data requires multi-factor authentication using a FIDO2 "
        "hardware security key.")),
    Doc("gold-sev1-ack", kind="gold", topic="incident", text=(
        "Incident Management Standard, Section 8.1. A Severity-1 incident must be "
        "acknowledged by the on-call incident commander within 5 minutes of the page.")),
]


EVAL_QUERIES: list[Query] = [
    Query("q-retention", "How long must completed customer transaction records be retained?",
          ["7 year", "seven year"], "gold-retention-txn", "retention"),
    Query("q-encrypt", "Which encryption standard is required for customer data at rest?",
          ["aes-256", "aes 256"], "gold-encrypt-rest", "encryption"),
    Query("q-breach", "Within what timeframe must the regulator be notified of a confirmed privacy breach?",
          ["72 hour", "72-hour"], "gold-breach-sla", "breach"),
    Query("q-approver", "Who is the sole approver for onboarding a new third-party data processor?",
          ["chief privacy officer", "cpo"], "gold-approver-processor", "approval"),
    Query("q-rpo", "What is the Recovery Point Objective (RPO) for the core banking database?",
          ["15 minute", "fifteen minute"], "gold-rpo-core", "rpo"),
    Query("q-residency", "Where must Canadian customer PII be stored?",
          ["toronto and montreal", "toronto", "montreal", "within canada"], "gold-residency-pii", "residency"),
    Query("q-mfa", "What MFA method is mandatory for production access?",
          ["fido2", "hardware security key"], "gold-mfa-prod", "mfa"),
    Query("q-sev1", "What is the acknowledgement SLA for a Severity-1 incident?",
          ["5 minute", "five minute"], "gold-sev1-ack", "incident"),
]


# ---------------------------------------------------------------------------
# DISTRACTORS — adversarial near-twins.
#
# Each distractor shares the gold chunk's head noun phrase and most of the
# query's salient terms, differing in ONE qualifier and the value. None contain
# a gold fact. A bi-encoder, which scores on overall term/semantic overlap,
# ranks many of these at or above the gold chunk — so the first-stage top-N is
# a pile of look-alikes. Only a cross-encoder, reading (query, doc) jointly, can
# tell "completed" from "pending" or "at rest" from "in transit".
#
# Each entry: (template with {q}/{v}, [qualifiers], [values]).
# Values deliberately exclude the gold answer tokens.
# ---------------------------------------------------------------------------

_TWINS = [
    # retention — gold: completed customer transaction records → 7 years
    ("Records Retention Standard. {q} customer transaction records must be retained "
     "for {v} from the settlement date before secure destruction.",
     ["Pending", "Disputed", "Reversed", "Failed", "Intraday", "Batch-settled",
      "Correspondent-bank", "FX", "Reconciliation", "Archived nightly"],
     ["30 days", "90 days", "18 months", "2 years", "3 years", "5 years", "10 years"]),

    # encryption — gold: customer data at rest → AES-256
    ("Cryptographic Standards. Customer data {q} must be encrypted using {v} with "
     "managed key rotation.",
     ["in transit between services", "in nightly backups", "in the analytics replica",
      "in non-production environments", "in cross-region replication streams",
      "at the field level for tokens", "on legacy archival volumes", "in message queues"],
     ["AES-128", "ChaCha20-Poly1305", "TLS 1.3", "RSA-2048 key wrap",
      "format-preserving encryption", "AES-192"]),

    # breach — gold: notify regulator within 72 hours of confirmation
    ("Privacy Breach Response. After a breach of customer personal information is "
     "confirmed, {q} must be completed within {v}.",
     ["internal escalation to the security team", "notification of affected customers",
      "a written report to the board", "notice to the cyber-insurer",
      "notice to the card network", "an internal post-incident review",
      "notice to law enforcement", "a preliminary triage summary"],
     ["1 hour", "24 hours", "48 hours", "5 business days", "30 days", "10 business days"]),

    # approval — gold: new data processor approved by Chief Privacy Officer
    ("Third-Party Risk Standard. {q} involving customer personal information must be "
     "approved by {v} before it proceeds.",
     ["A vendor security review", "A sub-processor contract renewal",
      "A data-processor offboarding", "A penetration-testing engagement",
      "An unbudgeted vendor spend increase", "A new analytics vendor's data feed",
      "A model vendor's API integration", "A vendor SLA exception"],
     ["the CISO", "the Chief Financial Officer", "the Change Advisory Board",
      "the Head of Procurement", "Legal", "the Chief Technology Officer"]),

    # rpo — gold: core banking database RPO 15 minutes
    ("Business Continuity Plan. {q} carries a Recovery Point Objective (RPO) of {v}.",
     ["The core banking read replica", "The reporting database",
      "The payments ledger archive", "The analytics data warehouse",
      "The fraud-scoring feature store", "The standby region's cold copy",
      "The customer-document store", "The reconciliation database"],
     ["0 (synchronous)", "5 minutes", "30 minutes", "1 hour", "4 hours", "24 hours"]),

    # rpo confusable: core banking RTO (not RPO) — shares "core banking" strongly
    ("Business Continuity Plan. The core banking database has a Recovery TIME "
     "Objective (RTO) of {v} for full service restoration.",
     [""],
     ["30 minutes", "1 hour", "2 hours", "4 hours"]),

    # residency — gold: Canadian customer PII only in Toronto and Montreal
    ("Data Residency Policy. {q} may be stored and processed in {v}, as it contains "
     "no Canadian customer personal information.",
     ["Aggregated de-identified analytics", "Public marketing content",
      "Application performance metrics", "Third-party support tickets",
      "Anonymised model-training extracts", "Vendor telemetry"],
     ["AWS us-east-1", "the EU (Frankfurt) region", "a global CDN",
      "the vendor's US data centre", "Microsoft 365's US tenancy", "GCP us-central1"]),

    # mfa — gold: production access requires FIDO2 hardware security key
    ("Access Control Standard. Human access to {q} requires multi-factor "
     "authentication using {v}.",
     ["the staging environment", "the corporate VPN", "the read-only analytics dashboard",
      "corporate email and chat", "the internal wiki", "a production read replica",
      "the CI/CD console", "the customer support tool"],
     ["a TOTP authenticator app", "a push approval on the mobile app",
      "an SMS one-time passcode", "a password plus IP allowlist", "an SSO session cookie"]),

    # incident — gold: Severity-1 acknowledged within 5 minutes
    ("Incident Management Standard. {q} must be acknowledged by the on-call engineer "
     "within {v} of the page.",
     ["A Severity-2 incident", "A Severity-3 incident", "A Severity-4 incident",
      "A planned-maintenance notice", "A status-page update", "A low-priority alert",
      "A non-customer-facing degradation"],
     ["15 minutes", "30 minutes", "1 hour", "2 hours", "the next business day"]),
]


def _distractor_bank() -> list[str]:
    """Expand every (template, qualifiers, values) twin into concrete sentences."""
    bank: list[str] = []
    for template, qualifiers, values in _TWINS:
        for q in qualifiers:
            for v in values:
                text = template.format(q=q, v=v).replace("  ", " ").strip()
                bank.append(text)
    return bank


# A few JSON-ish config chunks so the downstream SmartCrusher node has
# structured bloat to compress, mirroring Part 3's payload shape.
_JSON_CHUNKS = [
    Doc("cfg-access-matrix", kind="json", topic="config", text=(
        '{"access_matrix": [' +
        ", ".join(
            '{"role": "%s", "env": "%s", "mfa": "%s", "can_deploy": %s, "scope": "%s"}'
            % (r, e, m, d, s)
            for r, e, m, d, s in [
                ("analyst", "staging", "totp", "false", "read"),
                ("engineer", "staging", "totp", "true", "read-write"),
                ("engineer", "production", "fido2", "false", "read"),
                ("sre", "production", "fido2", "true", "read-write"),
                ("contractor", "staging", "push", "false", "read"),
            ]) +
        ']}')),
    Doc("cfg-backup-jobs", kind="json", topic="config", text=(
        '{"backup_jobs": [' +
        ", ".join(
            '{"system": "%s", "schedule": "%s", "encryption": "%s", "region": "%s", "retention_days": %d}'
            % (s, sch, enc, reg, ret)
            for s, sch, enc, reg, ret in [
                ("analytics_warehouse", "daily", "AES-128", "ca-central-1", 90),
                ("wiki", "weekly", "AES-128", "ca-central-1", 365),
                ("marketing_cms", "daily", "TLS-only", "global-cdn", 30),
                ("dev_sandbox", "none", "none", "local", 7),
            ]) +
        ']}')),
]


def build_corpus(n_distractors: int = 240, seed: int = 42) -> list[Doc]:
    """
    Assemble gold chunks + a deterministic sample of distractors + JSON config
    chunks, shuffled with a fixed seed so every run sees the same corpus.
    """
    rng = random.Random(seed)

    bank = _distractor_bank()
    rng.shuffle(bank)
    sampled = bank[:n_distractors]
    distractors = [
        Doc(f"distractor-{i:04d}", text=text, kind="prose", topic="distractor")
        for i, text in enumerate(sampled)
    ]

    corpus: list[Doc] = [*GOLD_CHUNKS, *_JSON_CHUNKS, *distractors]
    rng.shuffle(corpus)
    return corpus


def corpus_stats(corpus: list[Doc]) -> dict:
    kinds: dict[str, int] = {}
    for d in corpus:
        kinds[d.kind] = kinds.get(d.kind, 0) + 1
    return {"total": len(corpus), "by_kind": kinds}


if __name__ == "__main__":
    c = build_corpus()
    print("Corpus:", corpus_stats(c))
    print("Queries:", len(EVAL_QUERIES))
    print("Distractor templates available:", len(_distractor_bank()))
