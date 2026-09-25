"""CloudTrail record -> one Chaperone item.

The same record shape arrives from EventBridge (`detail`) and from LookupEvents
(`CloudTrailEvent`, a JSON string), so both ingest paths share this module.

Items are keyed by actor and time (D-020); sessions are derived when reading:

    PK = ACTOR#<actor>     SK = <eventTime>#<KIND>#<eventID>

KIND is API (an AWS API call), TOOL (an MCP tool call) or SIGNIN (credentials issued).
Writing the same record twice produces the same item, so both ingest paths are idempotent.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

from . import resources, rules

API, TOOL, SIGNIN = "API", "TOOL", "SIGNIN"

MCP_SOURCE = "aws-mcp.amazonaws.com"
RETENTION_DAYS = 90
PARAMS_MAX_BYTES = 4096

# User-agent fragments that identify a coding agent (lower-case match).
AGENT_USER_AGENTS = ("claude-code/", "mcp-proxy-for-aws", "kiro", "amazonq", "q-developer", "cursor/")

# Roles whose sessions are coding agents by identity (D-007: the agent has its own identity,
# so whatever tool it drives, Terraform or the CLI, the calls are the agent's).
AGENT_ROLE_PREFIXES = tuple(
    p for p in os.environ.get("AGENT_ROLE_PREFIXES", "AWSReservedSSO_ChaperoneAgent_").split(",") if p)

_DENIED = ("AccessDenied", "UnauthorizedOperation", "Client.UnauthorizedOperation", "UnauthorizedAccess")
_NOT_FOUND = re.compile(r"(^NoSuch|NotFound|^ResourceNotFound)")

# Chaperone's own roles (functions, forwarder). Recording them would add hundreds of rows
# an hour about Chaperone watching itself.
_SELF_ROLE = re.compile(r"^chaperone-")

# Who acted (the identity), independent of how the call was made (`via`).
HUMAN, AGENT, WORKLOAD, SERVICE = "human", "agent", "workload", "service"
SERVICE_RETENTION_DAYS = 7  # AWS services acting on their own: high volume, low review value


class Skip(Exception):
    """The record is valid but not something Chaperone records."""


def parse(record: dict | str) -> dict:
    return json.loads(record) if isinstance(record, str) else record


def actor_of(record: dict, resolve_idc=None) -> tuple[str, str]:
    """Return (actor key, arn) for the identity that acted.

    AssumedRole -> `role/<RoleName>/<SessionName>`, IAMUser -> `user/<name>`, Root -> `root`,
    AWSService -> `service/<name>`, FederatedUser -> `federated/<name>`,
    WebIdentityUser -> `web-identity/<provider>/<name>`, AWSAccount -> `account/<id>`.
    An Identity Center sign-in (AssumeRoleWithSAML) is filed under the role session it
    creates, so sign-ins land on the same timeline as the calls they enable.
    """
    uid = record.get("userIdentity") or {}
    kind = uid.get("type")

    if record.get("eventName") == "AssumeRoleWithSAML":
        arn = ((record.get("responseElements") or {}).get("assumedRoleUser") or {}).get("arn")
        if not arn:
            raise Skip("sign-in without an assumed role (failed)")
        return _role_key(arn), arn

    if kind == "AssumedRole":
        arn = uid.get("arn", "")
        key = _role_key(arn)
        role_name = key.split("/")[1]
        if _SELF_ROLE.match(role_name):
            raise Skip(f"Chaperone's own role {role_name}")
        return key, arn
    if kind == "IAMUser":
        return f"user/{uid.get('userName')}", uid.get("arn", "")
    if kind == "Root":
        return "root", uid.get("arn", "")
    if kind == "AWSService":
        # An AWS service acting on its own. Skip the ones assuming Chaperone's roles
        # (Lambda starting a function, EventBridge forwarding): that's Chaperone itself.
        role_arn = str((record.get("requestParameters") or {}).get("roleArn", ""))
        if ":role/chaperone-" in role_arn:
            raise Skip("AWS service assuming a Chaperone role")
        name = str(uid.get("invokedBy") or "unknown").removesuffix(".amazonaws.com")
        return f"service/{name}", ""
    if kind == "FederatedUser":
        return f"federated/{uid.get('principalId', '').split(':')[-1]}", uid.get("arn", "")
    if kind == "WebIdentityUser":
        return f"web-identity/{uid.get('identityProvider', '?')}/{uid.get('userName', '?')}", ""
    if kind == "AWSAccount":
        return f"account/{uid.get('accountId', '?')}", ""
    if kind == "IdentityCenterUser":
        # Portal calls (e.g. sso:GetRoleCredentials) name only the Identity Center user.
        # File them under the role session that user acts as, when known (store.py keeps
        # the mapping from events that carry both); otherwise under the user itself.
        user_id = (uid.get("onBehalfOf") or {}).get("userId", "?")
        known = resolve_idc(user_id) if resolve_idc else None
        return known or f"identity-center/{user_id}", ""
    raise Skip(f"identity type {kind!r} not recorded")


def actor_type(actor: str) -> str:
    """human, agent, workload (an application or CI role) or service (AWS acting on its own)."""
    if actor.startswith("role/"):
        role = actor.split("/")[1]
        if role.startswith(AGENT_ROLE_PREFIXES):
            return AGENT
        if role.startswith("AWSServiceRole"):
            return SERVICE
        if role.startswith("AWSReservedSSO_"):
            return HUMAN  # an Identity Center permission set used by a person
        return WORKLOAD
    if actor.startswith(("user/", "root", "federated/", "identity-center/")):
        return HUMAN
    if actor.startswith("service/"):
        return SERVICE
    return WORKLOAD  # web-identity (e.g. CI via OIDC), other accounts


def _role_key(assumed_role_arn: str) -> str:
    # arn:aws:sts::<acct>:assumed-role/<RoleName>/<SessionName>
    _, _, rest = assumed_role_arn.partition(":assumed-role/")
    role, _, session = rest.partition("/")
    return f"role/{role}/{session}"


def via_of(record: dict) -> str:
    """How the call was made: mcp, service:<name>, agent-cli, console, cli, sdk."""
    uid = record.get("userIdentity") or {}
    invoked_by = uid.get("invokedBy")
    ua = (record.get("userAgent") or "").lower().lstrip("[")
    if record.get("eventSource") == MCP_SOURCE or invoked_by == MCP_SOURCE:
        return "mcp"
    if invoked_by == "AWS Internal":
        return "console"  # the console calling AWS on the signed-in user's behalf
    if invoked_by:
        return f"service:{invoked_by.removesuffix('.amazonaws.com')}"
    if any(a in ua for a in AGENT_USER_AGENTS):
        return "agent-cli"
    if "terraform/" in ua:
        return "terraform"
    if ua.startswith(("console", "signin", "mozilla/", "aws internal")) or "console.amazonaws.com" in ua:
        return "console"
    if ua.startswith("aws-cli"):
        return "cli"
    return "sdk"


def operated_by(record: dict, via: str, who: str) -> str:
    """Who actually drove this call. Anything through MCP or an agent's CLI is an agent,
    whatever identity it used; otherwise it's the identity's type."""
    ua = (record.get("userAgent") or "").lower()
    if via in ("mcp", "agent-cli") or any(a in ua for a in AGENT_USER_AGENTS):
        return AGENT
    return who


def error_class(code: str) -> str:
    """denied (the interesting kind), not_found (tools probing optional settings), or other."""
    if code.startswith(_DENIED):
        return "denied"
    if _NOT_FOUND.search(code):
        return "not_found"
    return "other"


CREDENTIAL_EVENTS = {"AssumeRoleWithSAML", "GetRoleCredentials"}


def to_item(record: dict | str, resolve_idc=None) -> dict:
    """Normalize one CloudTrail record. Raises Skip for records Chaperone doesn't keep.
    `resolve_idc(user_id) -> actor or None` files Identity Center portal calls under the
    role session that user acts as."""
    r = parse(record)
    actor, arn = actor_of(r, resolve_idc)
    time = r["eventTime"]
    event_id = r["eventID"]
    name = r["eventName"]
    uid = r.get("userIdentity") or {}

    if name in CREDENTIAL_EVENTS:
        kind = SIGNIN  # credentials issued or fetched for this actor
    elif r.get("eventSource") == MCP_SOURCE:
        kind = TOOL
    else:
        kind = API
    via = via_of(r) if kind != SIGNIN else "identity-center"

    who = actor_type(actor)
    driver = operated_by(r, via, who) if kind != SIGNIN else who
    flags = []
    if driver == AGENT and who in (HUMAN, WORKLOAD):
        # The pattern D-007 avoids: an agent borrowing someone else's identity, so its
        # actions can't be told apart from theirs in IAM.
        flags.append(f"agent_on_{who}_identity")
    retention = SERVICE_RETENTION_DAYS if who == SERVICE else RETENTION_DAYS

    item = {
        "PK": f"ACTOR#{actor}",
        "SK": f"{time}#{kind}#{event_id}",
        "kind": kind,
        "actor": actor,
        "actor_arn": arn,
        "time": time,
        "event_id": event_id,
        "region": r.get("awsRegion"),
        "via": via,
        "actor_type": who,
        "operated_by": driver,
        "agent": driver == AGENT,
        "user_agent": r.get("userAgent"),
        "expires_at": _epoch(time) + retention * 86400,
    }
    if flags:
        item["flags"] = flags
    on_behalf = (uid.get("onBehalfOf") or {}).get("userId")
    if on_behalf:
        item["on_behalf_of"] = on_behalf
    if r.get("errorCode"):
        item["error_code"] = r["errorCode"]
        item["error_class"] = error_class(r["errorCode"])
        item["error_message"] = (r.get("errorMessage") or "")[:500]

    if kind == SIGNIN:
        item["risk"] = rules.READ
        return item

    if kind == TOOL:
        item.update(_tool_fields(r))
        return item

    service = rules.service_from_source(r["eventSource"])
    action = rules.normalize_action(name)
    params = r.get("requestParameters") or {}
    verdict = rules.classify(service, action, params, r.get("readOnly"))
    if not r.get("errorCode"):
        created, deleted = resources.refs(service, action, params, r.get("responseElements"))
        if created:
            item["creates"] = created
        if deleted:
            item["deletes"] = deleted
    item.update({
        "account": r.get("recipientAccountId"),
        "service": service,
        "action": action,
        "request_id": r.get("requestID"),
        "read_only": r.get("readOnly"),
        "risk": verdict.risk,
        "reasons": verdict.reasons,
        "resources": [x.get("ARN") for x in r.get("resources") or [] if x.get("ARN")],
        "params": _trim(params),
    })
    return item


def _tool_fields(r: dict) -> dict:
    """An MCP event. Tool arguments and results are hidden by AWS; what's left is the tool
    name and the AWS APIs it called. Risk is judged from those APIs by name only; the
    query layer re-judges with full parameters once the matching API items are joined."""
    req = r.get("requestParameters") or {}
    params = req.get("params") if isinstance(req.get("params"), dict) else {}
    downstream = []
    verdicts = []
    for d in (r.get("additionalEventData") or {}).get("downstreamRequests") or []:
        service, _, action = (d.get("apiName") or ":").partition(":")
        v = rules.classify(service, action)
        verdicts.append(v)
        downstream.append({
            "api": d.get("apiName"),
            "request_id": d.get("requestId"),
            "region": d.get("awsRegion"),
            "risk": v.risk,
        })
    top = rules.worst(verdicts)
    return {
        "method": req.get("method") or r.get("eventName"),
        "tool": params.get("name") or r.get("eventName"),
        "downstream": downstream,
        "risk": top.risk,
        "reasons": top.reasons,
    }


def _trim(params: dict) -> str:
    """Request parameters as JSON, cut to PARAMS_MAX_BYTES so one item stays small."""
    s = json.dumps(params, separators=(",", ":"), default=str)
    return s if len(s) <= PARAMS_MAX_BYTES else s[:PARAMS_MAX_BYTES] + "…(truncated)"


def _epoch(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def parse_time(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))

