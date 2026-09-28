"""Guardrails from what we saw: turn one session's risky calls into IAM policy proposals.

Built on AWS's own controls, not a new enforcement layer:

- Layer 1, the agent's identity: a deny policy for the agent's permission set or role. It
  covers every channel the agent uses (MCP, Terraform, CLI). On Day 1, 558 of the agent's
  calls went through Terraform, which an MCP-only rule would never see.
- Layer 2, the MCP channel: the same statements with `aws:ViaAWSMCPService = true`, for
  identities people share with their agents, or as an SCP across accounts. Key semantics
  from the AWS Security Blog, "Understanding IAM for Managed AWS MCP Servers" (2026-03-02).

Scoping keeps legitimate work working: a destructive or identity-escalation deny exempts
resources the agent created in the same session ("it may delete or grant on what it built,
nothing else"). Proposals are validated with IAM Access Analyzer before they are shown
(`aws_checks.validate`).
"""

from __future__ import annotations

import re

from . import rules
from .leftovers import arn_of
from .model import API

# CloudTrail event name -> IAM action(s) where they differ.
IAM_ACTION = {
    ("cloudfront", "CreateDistributionWithTags"): ["cloudfront:CreateDistribution", "cloudfront:TagResource"],
    ("s3", "DeleteBucketPublicAccessBlock"): ["s3:PutBucketPublicAccessBlock"],
    ("s3", "PutBucketPublicAccessBlock"): ["s3:PutBucketPublicAccessBlock"],
    ("s3", "GetBucketPublicAccessBlock"): ["s3:GetBucketPublicAccessBlock"],
    ("s3", "ListObjects"): ["s3:ListBucket"],
    ("s3", "ListObjectsV2"): ["s3:ListBucket"],
    ("s3", "HeadBucket"): ["s3:ListBucket"],
    ("s3", "DeleteBucketLifecycle"): ["s3:PutLifecycleConfiguration"],
    ("s3", "PutBucketLifecycle"): ["s3:PutLifecycleConfiguration"],
    ("s3", "GetBucketLifecycle"): ["s3:GetLifecycleConfiguration"],
    ("s3", "PutBucketEncryption"): ["s3:PutEncryptionConfiguration"],
    ("s3", "GetBucketEncryption"): ["s3:GetEncryptionConfiguration"],
    ("s3", "PutBucketVersioning"): ["s3:PutBucketVersioning"],
    ("s3", "GetBucketOwnershipControls"): ["s3:GetBucketOwnershipControls"],
    ("s3", "PutBucketOwnershipControls"): ["s3:PutBucketOwnershipControls"],
    ("s3", "ListBuckets"): ["s3:ListAllMyBuckets"],
    ("s3", "GetBucketCors"): ["s3:GetBucketCORS"],
    ("s3", "PutBucketCors"): ["s3:PutBucketCORS"],
    ("s3", "DeleteBucketCors"): ["s3:PutBucketCORS"],
    ("s3", "GetBucketReplication"): ["s3:GetReplicationConfiguration"],
    ("s3", "PutBucketReplication"): ["s3:PutReplicationConfiguration"],
    ("s3", "DeleteBucketReplication"): ["s3:PutReplicationConfiguration"],
    ("sso", "CreateAccountAssignment"): ["sso:CreateAccountAssignment"],
}

# Calls that pass a role to a service. CloudTrail never logs iam:PassRole itself, so neither
# this preview nor IAM Access Analyzer sees it; the role is in the request parameters.
PASSES_ROLE = {
    ("lambda", "CreateFunction"), ("lambda", "UpdateFunctionConfiguration"),
    ("events", "PutTargets"),
    ("ecs", "RegisterTaskDefinition"), ("ec2", "RunInstances"),
    ("ec2", "AssociateIamInstanceProfile"), ("cloudformation", "CreateStack"),
    ("cloudformation", "UpdateStack"), ("states", "CreateStateMachine"),
    ("glue", "CreateJob"), ("codebuild", "CreateProject"), ("scheduler", "CreateSchedule"),
}
ROLE_ARN = re.compile(r"arn:aws[\w-]*:iam::\d{12}:role/[\w+=,.@/-]+")

TITLES = {
    rules.AUDIT_TAMPERING: "Protect the audit trail",
    rules.IDENTITY_ESCALATION: "No new access, except on roles the agent built",
    rules.PUBLIC_EXPOSURE: "Nothing public without a person",
    rules.DESTRUCTIVE: "Delete only what the agent created",
}

ORDER = [rules.AUDIT_TAMPERING, rules.IDENTITY_ESCALATION, rules.PUBLIC_EXPOSURE, rules.DESTRUCTIVE]


def iam_actions(service: str, action: str) -> list[str]:
    return IAM_ACTION.get((service, action), [f"{service}:{action}"])


def _sid(text: str) -> str:
    return "".join(w.capitalize() for w in text.replace(",", "").replace("'", "").split())[:100]


def propose(items: list[dict], agent_role_arn: str | None = None) -> dict:
    """items: one session's items. Returns per-class findings and two policy documents."""
    apis = [i for i in items if i["kind"] == API and i.get("error_class") != "denied"]
    created_arns = sorted({
        a for i in apis for ref in i.get("creates", [])
        if (a := arn_of(ref, i.get("region"), i.get("account") or ""))})

    findings = []
    for risk in ORDER:
        hits = [i for i in apis if i["risk"] == risk]
        if not hits:
            continue
        actions = sorted({a for i in hits for a in iam_actions(i["service"], i["action"])})
        # Exempt what the agent built in this session, where "on what it built" makes sense.
        exempt = created_arns if risk in (rules.DESTRUCTIVE, rules.IDENTITY_ESCALATION) else []
        statement = {"Sid": _sid(TITLES[risk]), "Effect": "Deny", "Action": actions}
        if exempt:
            statement["NotResource"] = exempt
        else:
            statement["Resource"] = "*"
        findings.append({
            "risk": risk,
            "title": TITLES[risk],
            "evidence": [{"time": i["time"], "call": f"{i['service']}:{i['action']}", "via": i.get("via"),
                          "region": i.get("region"), "event_id": i["event_id"],
                          "reasons": i.get("reasons", [])} for i in hits],
            "statement": statement,
            "exempts_created": len(exempt),
        })

    statements = [f["statement"] for f in findings]
    mcp_statements = [{**s, "Sid": s["Sid"] + "ViaMCP",
                       "Condition": {"Bool": {"aws:ViaAWSMCPService": "true"}}} for s in statements]
    return {
        "findings": findings,
        "agent_identity_policy": {"Version": "2012-10-17", "Statement": statements} if statements else None,
        "mcp_channel_policy": {"Version": "2012-10-17", "Statement": mcp_statements} if statements else None,
        "applies_to": agent_role_arn,
        "notes": [
            "Agent identity policy: attach to the agent's permission set or role. Covers MCP, Terraform and CLI.",
            "MCP channel policy: aws:ViaAWSMCPService is true only for calls through an AWS-managed MCP server; "
            "use it on identities shared with agents, or as an SCP.",
            "Denies are scoped from this session's evidence; review before applying.",
        ],
    }


def least_privilege_preview(items: list[dict]) -> dict:
    """Instant preview: the IAM actions this session was allowed to use. IAM Access Analyzer's
    generated policy (aws_checks) adds resource ARNs; each side catches things the other misses.

    - A call that failed for any reason but access denied was still authorized
      (Terraform probing optional bucket settings gets NoSuchCORSConfiguration).
    - Calls AWS services made with the session's identity (via service:<name>, e.g. Lambda
      encrypting environment variables) are listed apart: the agent never called them.
    - iam:PassRole comes from the role ARNs in the request, scoped to those roles.
    """
    api = [i for i in items if i["kind"] == API and i.get("error_class") != "denied"]
    own = [i for i in api if not str(i.get("via", "")).startswith("service:")]
    used = sorted({a for i in own for a in iam_actions(i["service"], i["action"])})
    by_service: dict[str, list[str]] = {}
    for a in used:
        by_service.setdefault(a.split(":")[0], []).append(a)
    passed = sorted({arn.rstrip(".,") for i in own if (i["service"], i["action"]) in PASSES_ROLE
                     for arn in ROLE_ARN.findall(i.get("params") or "")})
    by_aws = sorted({f"{i['service']}:{i['action']} ({i['via'].split(':', 1)[1]})"
                     for i in api if str(i.get("via", "")).startswith("service:")})
    denied = sorted({f"{i['service']}:{i['action']}" for i in items
                     if i["kind"] == API and i.get("error_class") == "denied"})
    statements = [{"Sid": "UsedInSession", "Effect": "Allow", "Action": used, "Resource": "*"}] if used else []
    if passed:
        statements.append({"Sid": "PassedInSession", "Effect": "Allow", "Action": "iam:PassRole",
                           "Resource": passed})
    return {
        "actions": used,
        "by_service": by_service,
        "passed_roles": passed,
        "by_aws_services": by_aws,
        "denied_attempts": denied,
        "policy": {"Version": "2012-10-17", "Statement": statements} if statements else None,
    }
