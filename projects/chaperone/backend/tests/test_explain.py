"""Session explanations (D-029): the facts the model gets, and what comes back."""

import json

import pytest

from chaperone import explain, rules

from test_answers import day0_sessions


class FakeBedrock:
    def __init__(self, text):
        self.text, self.calls = text, []

    def converse(self, **kw):
        self.calls.append(kw)
        return {"output": {"message": {"content": [{"reasoningContent": {}}, {"text": self.text}]}},
                "usage": {"inputTokens": 10, "outputTokens": 5}}


GOOD = {"headline": "h", "summary": "s", "moments": [{"time": "t", "text": "chaperone‑api"}],
        "risk": "r", "access": "a"}


def test_facts_carry_exact_risk_counts_and_what_was_granted(day0):
    s, items = day0_sessions(day0)[-1]
    facts = explain.build_input(s, items)
    assert len(json.dumps(facts, default=str)) < 30_000
    assert facts["risky_counts"][rules.DESTRUCTIVE] == sum(
        c["count"] for c in facts["risky"][rules.DESTRUCTIVE]["calls"])
    assert facts["least_privilege"]["actions_used"] > 0
    assert "timeline" not in facts["session"]


def test_granted_only_where_known():
    assert "AdministratorAccess" in explain.granted("role/AWSReservedSSO_ChaperoneAgent_0000/chaperone-agent")
    assert explain.granted("user/admin") is None


def test_answer_parsed_fenced_and_hyphens_made_ascii():
    fenced = "```json\n" + json.dumps(GOOD) + "\n```"
    out, usage = explain.call_model({}, FakeBedrock(fenced))
    assert out["moments"][0]["text"] == "chaperone-api"
    assert usage["outputTokens"] == 5


def test_incomplete_answer_is_refused():
    with pytest.raises(ValueError):
        explain.call_model({}, FakeBedrock(json.dumps({"headline": "h"})))


def test_explanation_goes_stale_when_the_session_grows():
    s = {"session_id": "a@t", "end": "2026-09-25T19:00:00Z", "api_calls": 10, "tool_calls": 2}
    item = {"basis": explain.basis(s), "model": "m", "generated_at": "g", "explanation": GOOD}
    assert explain._view(item, s)["status"] == "READY"
    assert explain._view(item, {**s, "end": "2026-09-25T19:05:00Z", "api_calls": 12})["status"] == "STALE"


def test_headlines_join_the_session_list(monkeypatch):
    stored = [{"PK": "EXPLAIN#a@1", "SK": "v1", "explanation": {**GOOD, "headline": "Built the pipeline"}}]
    monkeypatch.setattr(explain.store, "get_many", lambda keys: stored)
    out = explain.with_headlines([{"session_id": "a@1"}, {"session_id": "b@2"}])
    assert out[0]["headline"] == "Built the pipeline" and "headline" not in out[1]
