"""
Simulated Extract -> Align -> Generate -> Refine pipeline.

This is a UI-focused prototype: it stands in for the real LangGraph nodes /
LLM Gateway calls / MongoDB reads described in implementation_plan.md so the
dashboard, live-transcript, and tweak-loop UX can be demoed end to end without
a live LLM or Mongo connection wired up yet. Swap these functions for real
node calls (extract_node.py, align_node.py, ...) without touching the UI.
"""
import json
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(name: str):
    with open(DATA_DIR / name) as f:
        return json.load(f)


PROSPECTS = _load("prospects.json")
RISK_RULES = _load("risk_alignment_rules.json")
FUND_SHEETS = _load("fund_fact_sheets.json")
PORTFOLIO_SNAPSHOTS = _load("portfolio_snapshots.json")
IPS_TEMPLATE = _load("ips_template.json")


def get_prospect(key: str) -> dict:
    return PROSPECTS[key]


def align_risk(risk_score: int) -> dict:
    """Node 2: Align — look up asset mix from the risk-alignment rule table."""
    for rule in RISK_RULES:
        if rule["risk_score_min"] <= risk_score <= rule["risk_score_max"]:
            return rule
    return RISK_RULES[-1]


def risk_tolerance_to_score(risk_tolerance: str) -> int:
    return {"conservative": 3, "moderate": 6, "aggressive": 9}[risk_tolerance]


def recommended_funds(equity_pct: int, n: int = 2) -> list[str]:
    equities = sorted(
        (f for f in FUND_SHEETS if f["asset_class"] == "Equity"),
        key=lambda f: abs(f["risk_rating"] - round(equity_pct / 10)),
    )
    fixed = sorted(
        (f for f in FUND_SHEETS if f["asset_class"] == "Fixed Income"),
        key=lambda f: f["risk_rating"],
    )
    picks = (equities[:n] if equity_pct >= 50 else fixed[:n]) or FUND_SHEETS[:n]
    return [f["fund_name"] for f in picks]


def generate_narrative(profile: dict, mix: dict, retirement_age: int, trigger: str) -> str:
    """Bakes in the same 5-row scripting rubric as PROPOSAL_SYNTHESIS_PROMPT
    (implementation_plan.md, Section 6), just templated instead of LLM-called."""
    goal = profile["goals"][-1] if profile["goals"] else "your long-term goals"
    flag = profile.get("concentration_flag", "")
    lines = []
    if trigger == "initial generation":
        lines.append(
            f"Based on the extracted profile, Risk Alignment selected a "
            f"{mix['equity_pct']}/{mix['fixed_income_pct']} equity-to-fixed-income mix."
        )
    else:
        lines.append(
            f"Refine has adjusted the proposal given '{trigger}' — now a "
            f"{mix['equity_pct']}/{mix['fixed_income_pct']} mix targeting retirement at age {retirement_age}."
        )
    lines.append(
        f"Given your mention of {goal.lower()} and that {flag.lower()}, "
        f"I've weighted this proposal accordingly rather than a generic model portfolio."
    )
    if "concentration" in flag.lower() or "idle" in flag.lower():
        lines.append(
            f"One thing worth flagging: {flag} — this proposal gradually rebalances that "
            f"exposure rather than realizing it all at once."
        )
    lines.append(
        "This is one clear recommended mix, not a spreadsheet of every fund considered — "
        "drag a slider if you'd like to see it adjust in real time."
    )
    lines.append(
        "This proposal is ready for your review in minutes, not days — no manual re-keying required."
    )
    return " ".join(lines)


def build_proposal(prospect_key: str, retirement_age: int, risk_tolerance: str, trigger: str) -> dict:
    """Runs Align -> Generate (and is reused by Refine) against the extracted profile."""
    prospect = PROSPECTS[prospect_key]
    profile = prospect["extracted_profile"]
    risk_score = risk_tolerance_to_score(risk_tolerance)
    rule = align_risk(risk_score)
    mix = {"equity_pct": rule["equity_pct"], "fixed_income_pct": rule["fixed_income_pct"]}
    narrative = generate_narrative(profile, mix, retirement_age, trigger)
    funds = recommended_funds(mix["equity_pct"])
    return {
        "asset_mix": mix,
        "risk_label": rule["label"],
        "narrative": narrative,
        "recommended_funds": funds,
        "retirement_age": retirement_age,
        "risk_tolerance": risk_tolerance,
    }


def build_ips(prospect_key: str, proposal: dict) -> dict:
    prospect = PROSPECTS[prospect_key]
    ips = dict(IPS_TEMPLATE)
    ips["client_id"] = prospect["client_id"]
    ips["target_asset_mix"] = proposal["asset_mix"]
    ips["compliance_flag"] = True
    ips["objective"] = prospect["extracted_profile"]["goals"][0]
    ips["time_horizon_years"] = max(proposal["retirement_age"] - 45, 1)
    return ips


def build_rebalance(prospect_key: str, proposal: dict) -> dict:
    client_id = PROSPECTS[prospect_key]["client_id"]
    snapshot = PORTFOLIO_SNAPSHOTS[client_id]
    current = snapshot["current_asset_mix"]
    target = proposal["asset_mix"]
    equity_delta = target["equity_pct"] - current["equity_pct"]
    trades = []
    if equity_delta > 0:
        for fund in proposal["recommended_funds"]:
            trades.append({"action": "BUY", "fund": fund, "pct_of_portfolio": round(abs(equity_delta) / max(len(proposal['recommended_funds']),1), 1)})
    else:
        trades.append({"action": "SELL", "fund": "Existing Equity Overweight", "pct_of_portfolio": round(abs(equity_delta), 1)})
    trades.append({"action": "REDEPLOY", "fund": "Fixed Income sleeve", "pct_of_portfolio": round(abs(equity_delta), 1)})
    return {
        "current_mix": current,
        "target_mix": target,
        "cash_position": snapshot["cash_position"],
        "trades": trades,
    }
