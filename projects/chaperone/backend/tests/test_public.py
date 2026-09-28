"""The public view (D-031): masking, the slim replay, and what the site may not do."""

import base64
import json

import pytest

from chaperone import model, public, query
from chaperone.sessions import sessionize
from chaperone import explain
from handlers import api

ACCOUNT = "444455556666"
ROLE = "role/AWSReservedSSO_ChaperoneAgent_a1b2c3d4e5f60718/chaperone-agent"
IDENTITY = "90676543-21a0-70b1-c2d3-e4f5a6b7c8d9"


def _item(**kw):
    base = {"kind": "API", "PK": f"ACTOR#{ROLE}", "SK": "t#API#e1", "event_id": "e1", "time": "2026-09-25T15:50:05Z",
            "actor": ROLE, "actor_arn": f"arn:aws:sts::{ACCOUNT}:assumed-role/{ROLE[5:]}", "service": "iam",
            "action": "PutRolePolicy", "risk": "identity_escalation", "reasons": ["iam:PutRolePolicy grants"],
            "request_id": "0f1e2d3c-4b5a-4968-8776-655443322110", "on_behalf_of": IDENTITY, "account": ACCOUNT,
            "via": "terraform", "region": "us-east-1", "user_agent": "Terraform/1.16.4 aws-sdk-go-v2/1.41.5",
            "params": json.dumps({"roleName": "chaperone-forwarder",
                                  "policyDocument": f"arn:aws:events:us-east-1:{ACCOUNT}:event-bus/default"})}
    return {**base, **kw}


def test_mask_removes_every_identifier():
    token = "IQoJb3JpZ2luX2VjE" + "A" * 300
    issuer = base64.b64encode(f'{{"a":"https://portal.sso.us-east-2.amazonaws.com/saml/{ACCOUNT}"}}'.encode()).decode()
    body = [_item(), {"note": f"from 198.51.100.7 and 2600:1f18:abcd:1200::17 key ASIAQWERTYUIOPASDFGH "
                              f"token {token} issuer {issuer} mail someone@example.org "
                              f"portal d-1234567890 dist E2ABCDEFGHIJKL "
                              f"url https://abcdefghijklmnopqrstuvwxyz012345.lambda-url.us-east-1.on.aws/ "
                              f"user {IDENTITY}"}]
    out = public.mask(body, ACCOUNT)
    for leak in (ACCOUNT, "a1b2c3d4e5f60718", IDENTITY, "198.51.100.7", "2600:1f18", "ASIAQWERTYUIOPASDFGH",
                 token[:40], "someone@", "d-1234567890", "E2ABCDEFGHIJKL", "abcdefghijklmnopqrstuvwxyz012345",
                 "0f1e2d3c-4b5a"):
        assert leak not in out, leak
    assert not any(c in out for c in public._base64_cores(ACCOUNT))
    # still useful: the story survives the masking
    assert "chaperone-forwarder" in out and "PutRolePolicy" in out and "Terraform/1.16.4 aws-sdk-go-v2/1.41.5" in out
    assert "2026-09-25T15:50:05Z" in out


def test_masked_session_id_comes_back():
    sid = f"{ROLE}@2026-09-25T15:49:07Z"
    masked = public.mask_text(sid, ACCOUNT)
    assert masked != sid
    assert public.unmask_session_id(masked, ["user/admin", ROLE], ACCOUNT) == sid


def test_replay_is_slim_and_keeps_the_flight_path(day0):
    items = [model.to_item(e) for e in day0]
    agent = [i for i in items if i.get("agent")]
    s = sessionize(agent)[-1]
    r = public.replay(s)
    assert len(r["marks"]) == len(s["timeline"])
    assert len(json.dumps(r)) < len(json.dumps(s, default=str)) / 2
    tools = [m for m in r["marks"] if m["kind"] == "TOOL"]
    assert tools and all(m["tool"] and m["calls"] for m in tools)
    assert {m["risk"] for m in r["marks"]} >= {"destructive"}
    one = next(c for m in tools for c in m["calls"] if c.get("event_id"))
    assert public.find_event(s, one["event_id"])["event_id"] == one["event_id"]


def _event(path, public_view=True, **q):
    return {"rawPath": path, "queryStringParameters": q,
            "headers": {"x-chaperone-view": "public"} if public_view else {},
            "requestContext": {"authorizer": {"iam": {"userArn": f"arn:aws:sts::{ACCOUNT}:assumed-role/X/me"}}}}


@pytest.fixture
def fake_store(monkeypatch):
    monkeypatch.setenv("ACCOUNT_ID", ACCOUNT)
    monkeypatch.setattr(api.store, "actors", lambda: [{"SK": ROLE}])
    seen = {}

    def session(sid):
        seen["sid"] = sid
        return {"session_id": sid, "actor": ROLE, "timeline": [_item()]}
    monkeypatch.setattr(query, "session", session)
    monkeypatch.setattr(query, "start_access_analyzer", lambda sid: pytest.fail("public view started a job"))
    monkeypatch.setattr(explain, "generate", lambda sid: pytest.fail("public view called a model"))
    return seen


def test_public_view_refuses_me_and_jobs(fake_store):
    assert api.handler(_event("/api/replay", id="me"), None)["statusCode"] == 403
    assert api.handler(_event("/api/replay"), None)["statusCode"] == 403
    assert api.handler(_event("/api/least-privilege", id=f"{ROLE}@x", start="1"), None)["statusCode"] == 403
    assert api.handler(_event("/api/session", id=f"{ROLE}@x"), None)["statusCode"] == 404  # full timeline: private
    assert api.handler(_event("/api/explain", id=f"{ROLE}@x", generate="1"), None)["statusCode"] == 403


def test_unknown_route_is_404_even_without_a_session_id(fake_store):
    assert api.handler(_event("/api/nope"), None)["statusCode"] == 404


def test_public_replay_unmasks_the_id_and_masks_the_answer(fake_store):
    masked = public.mask_text(f"{ROLE}@2026-09-25T15:49:07Z", ACCOUNT)
    r = api.handler(_event("/api/replay", id=masked), None)
    assert r["statusCode"] == 200 and r["headers"]["cache-control"].startswith("public")
    assert fake_store["sid"] == f"{ROLE}@2026-09-25T15:49:07Z"
    assert ACCOUNT not in r["body"] and "a1b2c3d4e5f60718" not in r["body"]
    assert json.loads(r["body"])["marks"][0]["api"] == "iam:PutRolePolicy"


def test_private_view_is_unchanged(fake_store):
    r = api.handler(_event("/api/session", public_view=False, id=f"{ROLE}@x"), None)
    assert r["statusCode"] == 200 and r["headers"]["cache-control"] == "no-store"
    assert ACCOUNT in r["body"]


def test_settled_sessions_are_cached_longer(fake_store):
    from datetime import datetime, timedelta, timezone
    recent = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for start, age in (("2020-01-01T00:00:00Z", 86400), (recent, 300)):
        masked = public.mask_text(f"{ROLE}@{start}", ACCOUNT)
        r = api.handler(_event("/api/replay", id=masked), None)
        assert r["statusCode"] == 200 and r["headers"]["cache-control"] == f"public, max-age={age}"
    assert api._max_age("/api/explain", f"{ROLE}@2020-01-01T00:00:00Z") == 3600
    assert api._max_age("/api/review", f"{ROLE}@2020-01-01T00:00:00Z") == 300  # checks live resources
    assert api._max_age("/api/sessions", None) == 60
