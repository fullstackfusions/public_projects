"""Compact answers (D-028) on the real Day 0 sessions."""

import json

from chaperone import answers, model, query, rules
from chaperone.model import API
from chaperone.sessions import sessionize


def day0_sessions(day0):
    items = [model.to_item(e) for e in day0]
    agent = [i for i in items if i.get("agent")]
    out = []
    for s in sessionize(agent):
        out.append((s, [i for i in agent if s["start"] <= i["time"] <= s["end"]]))
    return out


def test_what_happened_is_small_and_names_the_changes(day0):
    s, items = day0_sessions(day0)[-1]  # the probe: queue and rule, created then cleaned up
    w = answers.what_happened(s, items)
    assert len(json.dumps(w)) < 20_000
    assert {c["type"] for c in w["created"]} == {"AWS::SQS::Queue", "AWS::Events::Rule"}
    assert {c["type"] for c in w["deleted"]} == {"AWS::SQS::Queue", "AWS::Events::Rule"}
    assert all(c["action"] and c["count"] >= 1 for c in w["changes"])
    assert w["session"]["tool_calls"] == len(w["tool_calls"]) and all(t["tool"] for t in w["tool_calls"])


def test_risky_calls_mark_deletes_of_what_the_session_built(day0):
    s, items = day0_sessions(day0)[-1]
    r = answers.risky_calls(s, items)
    deletes = r["risky"][rules.DESTRUCTIVE]["calls"]
    assert deletes and all(c["on_resource_created_this_session"] for c in deletes)
    assert all(c.get("tool") for c in deletes)  # made through MCP tool calls


def test_repeats_collapse_and_truncated_params_still_name_the_target():
    base = {"kind": API, "SK": "x", "event_id": "x", "service": "iam", "action": "PutRolePolicy",
            "risk": rules.IDENTITY_ESCALATION, "reasons": [], "via": "terraform",
            "params": '{"roleName":"chaperone-poller","policyDocument":"{\\"Version\\":…(truncated)'}
    items = [{**base, "time": "2026-09-25T18:32:11Z"}, {**base, "time": "2026-09-25T18:39:53Z"}]
    s = {"session_id": "a@b", "actor": "a", "agent": True, "start": items[0]["time"], "end": items[1]["time"],
         "tool_calls": 0, "api_calls": 2, "denied": 0, "errors": 0, "risk": rules.IDENTITY_ESCALATION,
         "risk_counts": {}, "timeline": items}
    (row,) = answers.risky_calls(s, items)["risky"][rules.IDENTITY_ESCALATION]["calls"]
    assert row["target"] == "chaperone-poller" and row["count"] == 2 and row["last"] == "2026-09-25T18:39:53Z"


def test_caller_arn_to_actor():
    assert query.actor_from_arn("arn:aws:sts::111122223333:assumed-role/AWSReservedSSO_X_1/agent") == \
        "role/AWSReservedSSO_X_1/agent"
    assert query.actor_from_arn("arn:aws:iam::111122223333:user/admin") == "user/admin"
    assert query.actor_from_arn("arn:aws:iam::111122223333:root") == "root"
    assert query.actor_from_arn("") is None
    assert query.resolve("x@2026", None) == "x@2026"
