"""Deterministic risk rules: one AWS API call in, one risk class and its reasons out.

Pure functions, no AWS calls. The AI explains these results; it never decides them.
Classes, lowest to highest:

    read < write < destructive < public_exposure | identity_escalation | audit_tampering
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

READ = "read"
WRITE = "write"
DESTRUCTIVE = "destructive"
PUBLIC_EXPOSURE = "public_exposure"
IDENTITY_ESCALATION = "identity_escalation"
AUDIT_TAMPERING = "audit_tampering"

# Rank used for "the riskiest thing in this tool call / session".
SEVERITY = {
    READ: 0,
    WRITE: 1,
    DESTRUCTIVE: 2,
    PUBLIC_EXPOSURE: 3,
    IDENTITY_ESCALATION: 3,
    AUDIT_TAMPERING: 3,
}

READ_VERBS = ("BatchGet", "Get", "List", "Describe", "Lookup", "Search", "Head", "Check", "Query", "Scan", "Select",
              "Receive")
DESTRUCTIVE_VERBS = ("Delete", "Terminate", "Purge", "Destroy", "Deregister", "Remove")

AUDIT_TAMPERING_ACTIONS = {
    "cloudtrail": {"StopLogging", "DeleteTrail", "UpdateTrail", "PutEventSelectors", "DeleteEventDataStore"},
    "config": {"StopConfigurationRecorder", "DeleteConfigurationRecorder", "DeleteDeliveryChannel"},
    "guardduty": {"DeleteDetector", "DisassociateFromMasterAccount"},
    "securityhub": {"DisableSecurityHub"},
    "access-analyzer": {"DeleteAnalyzer"},
}

# iam:PassRole is a permission check, not an API call, so it never appears in CloudTrail.
IDENTITY_ESCALATION_ACTIONS = {
    "iam": {
        "AttachUserPolicy", "AttachRolePolicy", "AttachGroupPolicy",
        "PutUserPolicy", "PutRolePolicy", "PutGroupPolicy",
        "CreateAccessKey", "CreateLoginProfile", "UpdateLoginProfile",
        "UpdateAssumeRolePolicy", "CreatePolicyVersion", "SetDefaultPolicyVersion",
        "AddUserToGroup", "PutUserPermissionsBoundary", "DeleteUserPermissionsBoundary",
        "PutRolePermissionsBoundary", "DeleteRolePermissionsBoundary",
    },
    "sts": {"AssumeRole"},
    "sso": {
        "CreateAccountAssignment", "AttachManagedPolicyToPermissionSet",
        "PutInlinePolicyToPermissionSet", "AttachCustomerManagedPolicyReferenceToPermissionSet",
    },
}

# CloudTrail eventSource prefixes that differ from the IAM action prefix.
SOURCE_TO_PREFIX = {"monitoring": "cloudwatch", "email": "ses", "sso-admin": "sso"}

# Lambda (and a few others) put an API version on the event name: CreateFunction20150331,
# AddPermission20150331v2, UpdateDistribution2020_05_31.
_VERSION_SUFFIX = re.compile(r"(\d{8}(v\d+)?|\d{4}_\d{2}_\d{2})$")
_PUBLIC_CIDRS = {"0.0.0.0/0", "::/0"}
_PUBLIC_ACL_GROUPS = ("AllUsers", "AuthenticatedUsers")


@dataclass(frozen=True)
class Verdict:
    risk: str
    reasons: list[str] = field(default_factory=list)

    @property
    def severity(self) -> int:
        return SEVERITY[self.risk]


def service_from_source(event_source: str) -> str:
    """`s3.amazonaws.com` -> `s3`, `monitoring.amazonaws.com` -> `cloudwatch`."""
    prefix = event_source.removesuffix(".amazonaws.com")
    return SOURCE_TO_PREFIX.get(prefix, prefix)


def normalize_action(event_name: str) -> str:
    return _VERSION_SUFFIX.sub("", event_name)


def classify(service: str, action: str, params: dict | None = None, read_only: bool | None = None) -> Verdict:
    """Classify one API call. `params` are CloudTrail's requestParameters (None when unknown,
    e.g. a data event seen only in an MCP tool call's downstreamRequests)."""
    action = normalize_action(action)
    params = params or {}

    if action in AUDIT_TAMPERING_ACTIONS.get(service, ()):
        return Verdict(AUDIT_TAMPERING, [f"{service}:{action} changes or stops audit logging"])

    if action in IDENTITY_ESCALATION_ACTIONS.get(service, ()):
        return Verdict(IDENTITY_ESCALATION, [f"{service}:{action} grants or assumes more access"])

    exposure = _public_exposure(service, action, params)
    if exposure:
        return Verdict(PUBLIC_EXPOSURE, exposure)

    if action.startswith(DESTRUCTIVE_VERBS) or (service == "rds" and action.startswith("Stop")):
        return Verdict(DESTRUCTIVE, [f"{service}:{action} removes or stops a resource"])

    if read_only is True or (read_only is None and action.startswith(READ_VERBS)):
        return Verdict(READ)

    return Verdict(WRITE)


def worst(verdicts) -> Verdict:
    """The riskiest verdict, with every reason from verdicts of that class. Empty -> read."""
    verdicts = list(verdicts)
    if not verdicts:
        return Verdict(READ)
    top = max(verdicts, key=lambda v: v.severity)
    reasons = [r for v in verdicts if v.risk == top.risk for r in v.reasons]
    return Verdict(top.risk, list(dict.fromkeys(reasons)))


# --- public exposure -------------------------------------------------------------------

def _public_exposure(service: str, action: str, p: dict) -> list[str]:
    if service == "s3":
        if action == "PutBucketPolicy" and policy_is_public(p.get("bucketPolicy")):
            return [f"bucket policy on {p.get('bucketName', '?')} allows anyone (Principal *, no condition)"]
        if action == "DeleteBucketPublicAccessBlock":
            return [f"public access block removed from {p.get('bucketName', '?')}"]
        if action == "PutBucketPublicAccessBlock" and _pab_weakened(p.get("PublicAccessBlockConfiguration")):
            return [f"public access block weakened on {p.get('bucketName', '?')}"]
        if action in ("PutBucketAcl", "PutObjectAcl") and _acl_is_public(p):
            return [f"ACL on {p.get('bucketName', '?')} grants access to everyone"]
    if service == "s3control":
        if action == "DeletePublicAccessBlock":
            return ["account-level S3 public access block removed"]
        if action == "PutPublicAccessBlock" and _pab_weakened(p.get("PublicAccessBlockConfiguration")):
            return ["account-level S3 public access block weakened"]
    if service == "ec2":
        if action in ("AuthorizeSecurityGroupIngress",) and _ingress_is_open(p):
            return [f"security group {p.get('groupId', '?')} opened to the internet (0.0.0.0/0 or ::/0)"]
        if action == "ModifySnapshotAttribute" and _adds_group_all(p.get("createVolumePermission")):
            return [f"EBS snapshot {p.get('snapshotId', '?')} shared publicly"]
        if action == "ModifyImageAttribute" and _adds_group_all(p.get("launchPermission")):
            return [f"AMI {p.get('imageId', '?')} shared publicly"]
    if service == "lambda":
        if action in ("CreateFunctionUrlConfig", "UpdateFunctionUrlConfig") and p.get("authType") == "NONE":
            return [f"function URL on {p.get('functionName', '?')} needs no authentication"]
        if action == "AddPermission" and p.get("principal") == "*" and not (p.get("sourceArn") or p.get("sourceAccount")):
            return [f"{p.get('functionName', '?')} can be invoked by anyone"]
    if service == "rds":
        if action in ("ModifyDBInstance", "CreateDBInstance") and p.get("publiclyAccessible") is True:
            return [f"database {p.get('dBInstanceIdentifier', '?')} made publicly accessible"]
        if action in ("ModifyDBSnapshotAttribute", "ModifyDBClusterSnapshotAttribute") and "all" in (p.get("valuesToAdd") or []):
            return ["database snapshot shared publicly"]
    if service in ("sqs", "sns"):
        policy = (p.get("attributes") or {}).get("Policy") if service == "sqs" else (
            p.get("attributeValue") if p.get("attributeName") == "Policy" else None)
        if policy_is_public(policy):
            return [f"{service} resource policy allows anyone"]
    return []


def policy_is_public(policy) -> bool:
    """True if any Allow statement has Principal * (or AWS: *) and no Condition.
    A condition (SourceArn, SourceAccount, OrgID...) is treated as a restriction."""
    if isinstance(policy, str):
        if not policy:
            return False
        try:
            policy = json.loads(policy)
        except ValueError:
            return False
    if not isinstance(policy, dict):
        return False
    statements = policy.get("Statement") or []
    if isinstance(statements, dict):
        statements = [statements]
    for st in statements:
        if st.get("Effect") != "Allow" or st.get("Condition"):
            continue
        principal = st.get("Principal")
        if principal == "*":
            return True
        if isinstance(principal, dict):
            aws = principal.get("AWS")
            if aws == "*" or (isinstance(aws, list) and "*" in aws):
                return True
    return False


def _pab_weakened(cfg) -> bool:
    if not isinstance(cfg, dict):
        return False
    keys = ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")
    return any(str(cfg.get(k)).lower() == "false" for k in keys if k in cfg)


def _acl_is_public(p: dict) -> bool:
    if str(p.get("x-amz-acl", "")).startswith(("public-read", "authenticated-read")):
        return True
    return any(g in json.dumps(p.get("AccessControlPolicy") or {}) for g in _PUBLIC_ACL_GROUPS)


def _ingress_is_open(p: dict) -> bool:
    if p.get("cidrIp") in _PUBLIC_CIDRS:
        return True
    for perm in (p.get("ipPermissions") or {}).get("items", []):
        for r in (perm.get("ipRanges") or {}).get("items", []):
            if r.get("cidrIp") in _PUBLIC_CIDRS:
                return True
        for r in (perm.get("ipv6Ranges") or {}).get("items", []):
            if r.get("cidrIpv6") in _PUBLIC_CIDRS:
                return True
    return False


def _adds_group_all(perm) -> bool:
    if not isinstance(perm, dict):
        return False
    for item in (perm.get("add") or {}).get("items", []):
        if item.get("group") == "all":
            return True
    return False
