"""
Evaluation queries for the two real PDFs.

Each query carries:
  question     — the natural-language question sent to the pipeline
  gold         — list of substrings; answer is "correct" if ANY appears (case-insensitive)
  source_hint  — which PDF is expected to contain the answer (for source-attribution check)
  topic        — short label for grouping in the result table

These are verifiable from the actual document content; gold strings were chosen
to be distinctive (appearing in the answer section, not in near-duplicates).

If you swap in different PDFs, replace or extend this list with queries whose
gold facts are confirmed in your documents.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Query:
    id: str
    question: str
    gold: list[str]
    source_hint: str    # "ml_trading" | "law_compliance" | "both"
    topic: str


EVAL_QUERIES: list[Query] = [
    # ── Machine Learning for Algorithmic Trading ─────────────────────────────
    Query(
        "ml-sharpe",
        "What is the Sharpe ratio and how is it used to evaluate trading strategies?",
        ["sharpe ratio", "risk-adjusted", "excess return", "standard deviation"],
        "ml_trading",
        "portfolio evaluation",
    ),
    Query(
        "ml-backtest-bias",
        "What are the main sources of bias in backtesting trading strategies?",
        ["lookahead bias", "survivorship bias", "overfitting", "data snooping"],
        "ml_trading",
        "backtesting",
    ),
    Query(
        "ml-feature-importance",
        "How are feature importance scores used in machine learning models for trading?",
        ["feature importance", "random forest", "gradient boosting", "alpha factor"],
        "ml_trading",
        "feature engineering",
    ),
    Query(
        "ml-nlp-sentiment",
        "How is natural language processing (NLP) applied to financial news for trading signals?",
        ["sentiment", "news", "text", "nlp", "natural language"],
        "ml_trading",
        "NLP for finance",
    ),
    Query(
        "ml-risk-mgmt",
        "What risk management techniques are described for algorithmic trading portfolios?",
        ["drawdown", "volatility", "position sizing", "kelly", "risk"],
        "ml_trading",
        "risk management",
    ),
    Query(
        "ml-reinforcement",
        "How is reinforcement learning applied to trading and portfolio management?",
        ["reinforcement learning", "reward", "agent", "policy", "q-learning"],
        "ml_trading",
        "RL for trading",
    ),

    # ── Law & Compliance in AI / Security / Data Protection ──────────────────
    Query(
        "law-ai-act-risk",
        "How does the EU AI Act classify AI systems into risk categories?",
        ["unacceptable risk", "high-risk", "limited risk", "minimal risk", "prohibited"],
        "law_compliance",
        "AI Act risk tiers",
    ),
    Query(
        "law-gdpr-breach",
        "What are the notification obligations following a personal data breach under GDPR?",
        ["72 hour", "supervisory authority", "data breach", "notification", "without undue delay"],
        "law_compliance",
        "GDPR breach",
    ),
    Query(
        "law-data-minimisation",
        "What does the data minimisation principle require under data protection law?",
        ["data minimisation", "minimization", "adequate", "relevant", "limited"],
        "law_compliance",
        "data minimisation",
    ),
    Query(
        "law-high-risk-ai",
        "What conformity assessment obligations apply to high-risk AI systems?",
        ["conformity assessment", "high-risk", "technical documentation", "human oversight"],
        "law_compliance",
        "AI conformity",
    ),
    Query(
        "law-security-ai",
        "What cybersecurity measures are recommended for AI systems processing personal data?",
        ["encryption", "access control", "security measure", "pseudonymisation", "integrity"],
        "law_compliance",
        "AI security",
    ),

    # ── Cross-document ────────────────────────────────────────────────────────
    Query(
        "cross-ml-privacy",
        "What privacy or data protection considerations apply when using machine learning "
        "models trained on personal data?",
        ["privacy", "personal data", "gdpr", "data protection", "anonymi"],
        "both",
        "ML + privacy",
    ),
]
