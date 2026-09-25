"""Normalizing real Day 0 records and rebuilding the session from them."""

import pytest

from chaperone import model, rules
from chaperone.model import API, SIGNIN, TOOL
from chaperone.sessions import sessionize
from conftest import by_name

AGENT = "role/AWSReservedSSO_ChaperoneAgent_0123456789abcdef/chaperone-agent"


def items_of(events):
    out = []
    for e in events:
        try:
            out.append(model.to_item(e))
        except model.Skip:
            pass
    return out


def test_every_day0_event_is_kept_and_filed_under_the_agent(day0):
    items = items_of(day0)
    assert len(items) == len(day0) == 90
    assert {i["actor"] for i in items} == {AGENT}
    assert {i["kind"] for i in items} == {API, TOOL, SIGNIN}


def test_keys_are_deterministic(day0):
    e = day0[10]
    assert model.to_item(e) == model.to_item(dict(e))
    assert model.to_item(e)["SK"].startswith(e["eventTime"])


def test_mcp_tool_call(day0):
    tools = [model.to_item(e) for e in by_name(day0, "CallReadWriteTool")]
    assert len(tools) == 14
    big = max(tools, key=lambda t: len(t["downstream"]))
    assert big["tool"] == "aws___run_script"
    assert big["via"] == "mcp" and big["agent"] is True
    assert {d["api"] for d in big["downstream"]} == {"cloudtrail:LookupEvents"}
    assert big["risk"] == rules.READ  # labelled readOnly=false by AWS, judged by its APIs


def test_api_call_made_through_mcp(day0):
    (e,) = by_name(day0, "CreateBucket")
    i = model.to_item(e)
    assert (i["kind"], i["service"], i["action"], i["via"], i["risk"]) == (API, "s3", "CreateBucket", "mcp", "write")
    assert i["on_behalf_of"] == "00000000-1111-2222-3333-444444444444"


def test_service_acting_for_the_agent(day0):
    (e,) = by_name(day0, "CreateGrant")
    assert model.to_item(e)["via"] == "service:acm"


def test_signin_filed_under_the_role_session_it_creates(day0):
    i = model.to_item(by_name(day0, "AssumeRoleWithSAML")[0])
    assert i["kind"] == SIGNIN and i["actor"] == AGENT


def test_chaperone_own_roles_are_skipped():
    own = {"eventName": "LookupEvents", "eventTime": "2026-09-25T00:00:00Z", "eventID": "x",
           "userIdentity": {"type": "AssumedRole", "arn": "arn:aws:sts::111122223333:assumed-role/chaperone-poller/f"}}
    with pytest.raises(model.Skip):
        model.to_item(own)
    forwarder = {"eventName": "AssumeRole", "eventTime": "2026-09-25T00:00:00Z", "eventID": "y",
                 "eventSource": "sts.amazonaws.com",
                 "userIdentity": {"type": "AWSService", "invokedBy": "events.amazonaws.com"},
                 "requestParameters": {"roleArn": "arn:aws:iam::111122223333:role/chaperone-forwarder"}}
    with pytest.raises(model.Skip):
        model.to_item(forwarder)


def test_lookup_events_string_form_is_accepted(day0):
    import json
    assert model.to_item(json.dumps(day0[0])) == model.to_item(day0[0])


def test_params_are_trimmed():
    e = {"eventName": "PutThing", "eventTime": "2026-09-25T00:00:00Z", "eventID": "x", "eventSource": "s3.amazonaws.com",
         "userIdentity": {"type": "IAMUser", "userName": "admin", "arn": "arn:aws:iam::111122223333:user/admin"},
         "requestParameters": {"blob": "x" * 10_000}}
    i = model.to_item(e)
    assert i["actor"] == "user/admin" and i["agent"] is False
    assert len(i["params"]) < model.PARAMS_MAX_BYTES + 20 and i["params"].endswith("(truncated)")


# --- sessions -----------------------------------------------------------------------------

def test_day0_sessions(day0):
    sessions = sessionize(items_of(day0))
    assert sessions, "at least one session"
    s = max(sessions, key=lambda s: s["api_calls"])
    assert s["agent"] is True
    assert s["tool_calls"] >= 1 and s["signins"] >= 1
    # Day 0 deleted its EventBridge probe, so the riskiest thing is destructive.
    assert rules.SEVERITY[s["risk"]] >= rules.SEVERITY["write"]
    for t in s["timeline"]:
        assert t["kind"] in (API, TOOL)


def test_tool_calls_claim_their_api_calls(day0):
    items = items_of(day0)
    total_claimable = sum(len(i["downstream"]) for i in items if i["kind"] == TOOL)
    for s in sessionize(items):
        tools = [t for t in s["timeline"] if t["kind"] == TOOL]
        shown_apis = [t for t in s["timeline"] if t["kind"] == API]
        joined = [c for t in tools for c in t["calls"] if c.get("kind") == API]
        # every API made through MCP is shown once, under its tool call
        assert not {a["request_id"] for a in shown_apis} & {c["request_id"] for c in joined}
    assert total_claimable > 0


def test_sessions_split_on_idle_gap_and_ignore_input_order():
    def item(t, sk):
        return {"PK": "ACTOR#a", "SK": f"{t}#API#{sk}", "kind": API, "actor": "a", "time": t,
                "risk": "read", "request_id": sk}
    items = [item("2026-09-25T10:00:00Z", "1"), item("2026-09-25T10:20:00Z", "2"),
             item("2026-09-25T11:00:00Z", "3")]
    s = sessionize(list(reversed(items)))
    assert [x["api_calls"] for x in s] == [2, 1]
    assert s[0]["session_id"] == "a@2026-09-25T10:00:00Z"


# --- found on the first live run (2026-09-25) ----------------------------------------------

def _agent_record(ua, **extra):
    return {"eventName": "GetBucketCors", "eventTime": "2026-09-25T14:10:00Z", "eventID": "e1",
            "eventSource": "s3.amazonaws.com", "userAgent": ua, "readOnly": True,
            "userIdentity": {"type": "AssumedRole", "arn": f"arn:aws:sts::111122223333:assumed-role/{AGENT.split('/', 1)[1]}"},
            **extra}


def test_terraform_run_by_the_agent_identity_is_the_agent():
    i = model.to_item(_agent_record("APN/1.0 HashiCorp/1.0 Terraform/1.16.4 (+https://www.terraform.io)"))
    assert i["via"] == "terraform" and i["agent"] is True


def test_bracketed_cli_user_agent():
    assert model.to_item(_agent_record("[aws-cli/2.37.3 md/awscrt#0.37.0]"))["via"] == "cli"


def test_human_identity_is_not_an_agent():
    r = _agent_record("aws-cli/2.37.3", userIdentity={"type": "IAMUser", "userName": "admin",
                                                     "arn": "arn:aws:iam::111122223333:user/admin"})
    assert model.to_item(r)["agent"] is False


@pytest.mark.parametrize("code,cls", [("NoSuchCORSConfiguration", "not_found"),
                                      ("ReplicationConfigurationNotFoundError", "not_found"),
                                      ("AccessDenied", "denied"), ("Client.UnauthorizedOperation", "denied"),
                                      ("OperationAborted", "other")])
def test_error_classes(code, cls):
    assert model.to_item(_agent_record("x", errorCode=code))["error_class"] == cls


def test_console_internal_calls_are_console():
    r = _agent_record("AWS Internal", userIdentity={"type": "IAMUser", "userName": "admin", "invokedBy": "AWS Internal",
                                                   "arn": "arn:aws:iam::111122223333:user/admin"})
    assert model.to_item(r)["via"] == "console"


# --- who acted vs how (D-024) ----------------------------------------------------------------

def _rec(identity, ua="aws-cli/2.37.3", **extra):
    return {"eventName": "DescribeInstances", "eventTime": "2026-09-25T15:00:00Z", "eventID": "z",
            "eventSource": "ec2.amazonaws.com", "userAgent": ua, "readOnly": True,
            "userIdentity": identity, **extra}


SSO_HUMAN = {"type": "AssumedRole",
             "arn": "arn:aws:sts::111122223333:assumed-role/AWSReservedSSO_AdministratorAccess_abc/mihir"}


def test_day0_agent_items_are_agent_typed(day0):
    for i in items_of(day0):
        if i["kind"] != SIGNIN:
            assert (i["actor_type"], i["operated_by"]) == ("agent", "agent")
            assert "flags" not in i


def test_human_in_console():
    i = model.to_item(_rec({"type": "IAMUser", "userName": "admin", "arn": "arn:aws:iam::111122223333:user/admin"},
                           ua="Mozilla/5.0"))
    assert (i["actor_type"], i["operated_by"], i["via"]) == ("human", "human", "console")


def test_agent_through_mcp_on_a_human_identity_is_flagged():
    i = model.to_item(_rec({**SSO_HUMAN, "invokedBy": "aws-mcp.amazonaws.com"}, ua="aws-mcp.amazonaws.com"))
    assert (i["actor_type"], i["operated_by"], i["via"]) == ("human", "agent", "mcp")
    assert i["flags"] == ["agent_on_human_identity"]


def test_agent_cli_on_a_human_identity_is_flagged():
    i = model.to_item(_rec(SSO_HUMAN, ua="aws-cli/2.37.3 claude-code/2.1.280"))
    assert i["operated_by"] == "agent" and i["flags"] == ["agent_on_human_identity"]


def test_aws_service_on_its_own_is_kept_briefly():
    i = model.to_item(_rec({"type": "AWSService", "invokedBy": "resource-explorer-2.amazonaws.com"}, ua="x"))
    assert (i["actor"], i["actor_type"], i["operated_by"]) == ("service/resource-explorer-2", "service", "service")
    assert i["expires_at"] - model._epoch(i["time"]) == 7 * 86400


def test_service_linked_role_is_a_service():
    i = model.to_item(_rec({"type": "AssumedRole", "arn":
                            "arn:aws:sts::111122223333:assumed-role/AWSServiceRoleForResourceExplorer/x"}, ua="x"))
    assert i["actor_type"] == "service"


def test_ci_role_is_a_workload():
    i = model.to_item(_rec({"type": "AssumedRole", "arn": "arn:aws:sts::111122223333:assumed-role/github-deploy/run-42"}))
    assert (i["actor_type"], i["operated_by"]) == ("workload", "workload")


def test_other_identity_types_are_recorded():
    assert model.to_item(_rec({"type": "WebIdentityUser", "identityProvider": "token.actions.githubusercontent.com",
                               "userName": "repo:x/y"}))["actor_type"] == "workload"
    assert model.to_item(_rec({"type": "FederatedUser", "principalId": "111122223333:bob",
                               "arn": "arn:aws:sts::111122223333:federated-user/bob"}))["actor_type"] == "human"
    assert model.to_item(_rec({"type": "AWSAccount", "accountId": "444455556666"}))["actor"] == "account/444455556666"


def test_session_summary_counts_who_drove(day0):
    s = max(sessionize(items_of(day0)), key=lambda s: s["api_calls"])
    assert s["actor_type"] == "agent" and set(s["operated_by"]) == {"agent"} and s["flags"] == []


def test_identity_center_credential_fetch_is_filed_under_the_agent():
    r = {"eventName": "GetRoleCredentials", "eventTime": "2026-09-25T18:40:00Z", "eventID": "gc1",
         "eventSource": "sso.amazonaws.com", "userAgent": "Boto3/1.43.82",
         "userIdentity": {"type": "IdentityCenterUser", "onBehalfOf": {"userId": "00000000-1111-2222-3333-444444444444"}}}
    i = model.to_item(r, resolve_idc={"00000000-1111-2222-3333-444444444444": AGENT}.get)
    assert (i["kind"], i["actor"], i["actor_type"]) == (SIGNIN, AGENT, "agent")
    unknown = model.to_item(r, resolve_idc=lambda _: None)
    assert (unknown["actor"], unknown["actor_type"]) == ("identity-center/00000000-1111-2222-3333-444444444444", "human")
