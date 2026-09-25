"""Left running + guardrails + least privilege on the real Day 0 sessions."""

import json

from chaperone import guardrails, leftovers, model, rules
from chaperone.model import API
from chaperone.sessions import sessionize

ACCT = "111122223333"


def day0_items(day0):
    return [model.to_item(e) for e in day0]


def everything_exists(ref):
    return leftovers.EXISTS, "test"


def test_day0_left_running_vs_cleaned_up(day0):
    r = leftovers.analyze(day0_items(day0), everything_exists)
    running = {x["type"] for x in r["left_running"]}
    assert running == {"AWS::S3::Bucket", "AWS::CloudFront::Distribution",
                       "AWS::CloudFront::OriginAccessControl", "AWS::CertificateManager::Certificate"}
    assert {x["type"] for x in r["cleaned_up"]} == {"AWS::SQS::Queue", "AWS::Events::Rule"}
    assert r["removed_preexisting"] == []
    assert r["idle_usd_month"] == 0.0  # the hello-world site costs nothing while idle


def test_resource_gone_after_session_is_not_left_running(day0):
    r = leftovers.analyze(day0_items(day0), lambda ref: (leftovers.GONE, "404"))
    assert r["left_running"] == [] and len(r["removed_later"]) == 4


def test_deleting_something_the_agent_did_not_create(day0):
    items = day0_items(day0)
    rogue = {**items[-1], "kind": API, "SK": "z", "time": "2026-09-25T03:19:00Z", "event_id": "rogue",
             "service": "s3", "action": "DeleteBucket", "risk": rules.DESTRUCTIVE,
             "deletes": [{"type": "AWS::S3::Bucket", "id": "prod-customer-data"}], "creates": []}
    r = leftovers.analyze(items + [rogue], everything_exists)
    assert [x["id"] for x in r["removed_preexisting"]] == ["prod-customer-data"]


def test_day0_guardrail_allows_its_own_cleanup(day0):
    probe = sessionize(day0_items(day0))[1]  # the EventBridge probe session
    items = [i for i in day0_items(day0) if probe["start"] <= i["time"] <= probe["end"]]
    g = guardrails.propose(items)
    (f,) = g["findings"]
    assert f["risk"] == rules.DESTRUCTIVE
    st = f["statement"]
    assert st["Action"] == ["events:DeleteRule", "events:RemoveTargets", "sqs:DeleteQueue"]
    # The queue and rule it deleted were created in the same session, so they're exempt.
    assert f"arn:aws:sqs:us-east-1:{ACCT}:chaperone-eb-probe" in st["NotResource"]
    assert f"arn:aws:events:us-east-1:{ACCT}:rule/chaperone-eb-probe" in st["NotResource"]
    mcp = g["mcp_channel_policy"]["Statement"][0]
    assert mcp["Condition"] == {"Bool": {"aws:ViaAWSMCPService": "true"}}
    assert mcp["Sid"].endswith("ViaMCP")


def test_guardrail_for_escalation_and_audit_tampering():
    def api(action, service, risk, **kw):
        return {"kind": API, "SK": action, "time": "2026-09-25T14:20:00Z", "event_id": action, "service": service,
                "action": action, "risk": risk, "region": "us-east-1", "account": ACCT, "via": "terraform", **kw}
    items = [api("CreateRole", "iam", rules.WRITE, creates=[{"type": "AWS::IAM::Role", "id": "chaperone-ingest"}]),
             api("PutRolePolicy", "iam", rules.IDENTITY_ESCALATION),
             api("UpdateTrail", "cloudtrail", rules.AUDIT_TAMPERING, region="us-east-2")]
    g = guardrails.propose(items)
    assert [f["risk"] for f in g["findings"]] == [rules.AUDIT_TAMPERING, rules.IDENTITY_ESCALATION]
    audit, esc = g["findings"]
    assert audit["statement"] == {"Sid": "ProtectTheAuditTrail", "Effect": "Deny",
                                  "Action": ["cloudtrail:UpdateTrail"], "Resource": "*"}
    assert esc["statement"]["NotResource"] == [f"arn:aws:iam::{ACCT}:role/chaperone-ingest"]
    json.dumps(g)  # serializable for the API


def test_no_risk_no_guardrail():
    g = guardrails.propose([{"kind": API, "SK": "a", "time": "t", "event_id": "a", "service": "s3",
                             "action": "GetBucketPolicy", "risk": rules.READ}])
    assert g["findings"] == [] and g["agent_identity_policy"] is None


def test_least_privilege_preview_maps_event_names(day0):
    lp = guardrails.least_privilege_preview(day0_items(day0))
    assert "cloudfront:CreateDistribution" in lp["actions"] and "cloudfront:TagResource" in lp["actions"]
    assert "cloudfront:CreateDistributionWithTags" not in lp["actions"]
    assert "s3:GetBucketPublicAccessBlock" in lp["actions"]
    assert lp["denied_attempts"] == []


def test_put_rule_on_a_known_rule_is_an_update_not_a_leftover(day0):
    items = day0_items(day0)
    (rule,) = [i for i in items if i.get("action") == "PutRule"]
    assert rule["creates"][0]["upsert"] is True
    probe_items = [i for i in items if i["time"] >= "2026-09-25T03:13"]
    before = leftovers.created_keys(probe_items)  # pretend it was recorded earlier
    r = leftovers.analyze([i for i in probe_items if i.get("action") != "DeleteRule"], everything_exists, before)
    assert "AWS::Events::Rule" not in {x["type"] for x in r["left_running"]}
    r = leftovers.analyze([i for i in probe_items if i.get("action") != "DeleteRule"], everything_exists)
    assert [x.get("upsert") for x in r["left_running"] if x["type"] == "AWS::Events::Rule"] == [True]


def _api(service, action, **kw):
    return {"kind": API, "SK": action, "time": "t", "event_id": action, "service": service,
            "action": action, "risk": rules.READ, **kw}


def test_least_privilege_preview_matches_access_analyzer_semantics():
    """The differences found against Access Analyzer on the Day 1 build session."""
    role = f"arn:aws:iam::{ACCT}:role/chaperone-ingest"
    lp = guardrails.least_privilege_preview([
        _api("s3", "GetBucketCors", error_code="NoSuchCORSConfiguration", error_class="not_found"),
        _api("s3", "GetBucketReplication", error_code="ReplicationConfigurationNotFoundError",
             error_class="not_found"),
        _api("s3", "ListBuckets", via="cli"),
        _api("s3", "PutBucketPolicy", error_code="AccessDenied", error_class="denied"),
        _api("kms", "Decrypt", via="service:lambda"),
        _api("lambda", "CreateFunction", via="terraform",
             params=f'{{"functionName":"chaperone-ingest","role":"{role}"}}'),
    ])
    assert lp["actions"] == ["lambda:CreateFunction", "s3:GetBucketCORS", "s3:GetReplicationConfiguration",
                             "s3:ListAllMyBuckets"]
    assert lp["by_aws_services"] == ["kms:Decrypt (lambda)"]
    assert lp["denied_attempts"] == ["s3:PutBucketPolicy"]
    assert lp["passed_roles"] == [role]
    assert lp["policy"]["Statement"][1] == {"Sid": "PassedInSession", "Effect": "Allow",
                                           "Action": "iam:PassRole", "Resource": [role]}


def test_least_privilege_comparison_with_access_analyzer():
    from chaperone import query
    items = [_api("logs", "FilterLogEvents", via="cli"), _api("s3", "ListBuckets", via="cli")]
    aa = {"status": "SUCCEEDED", "policies": [json.dumps({"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Action": ["s3:ListAllMyBuckets", "organizations:ListAWSServiceAccessForOrganization"],
         "Resource": "*"}]})]}
    c = query.least_privilege(items, aa)["comparison"]
    assert c == {"shared": 1, "service_level_only": [], "only_chaperone": ["logs:FilterLogEvents"],
                 "only_access_analyzer": ["organizations:ListAWSServiceAccessForOrganization"],
                 "missed_by_both_recovered": []}
    assert "comparison" not in query.least_privilege(items, {"status": "IN_PROGRESS"})
