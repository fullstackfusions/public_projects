"""The query layer: the three questions, answered from the table (D-017).

    1. What did the agent do?        sessions() / session()
    2. Was anything risky?           session() risk + review() guardrails
    3. What access does it need?     review() least-privilege preview + Access Analyzer job

Shared by the HTTP API, the MCP server and the web console.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

from . import answers, aws_checks, guardrails, leftovers, store
from .model import parse_time
from .sessions import sessionize

WINDOW = timedelta(hours=24)  # longest session we reconstruct from a start time


def _iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def split_id(session_id: str) -> tuple[str, str]:
    actor, _, start = session_id.rpartition("@")
    if not actor or not start:
        raise ValueError(f"bad session id {session_id!r}")
    return actor, start


def sessions(days: int = 7, include_services: bool = False) -> list[dict]:
    since = _iso(datetime.now(timezone.utc) - timedelta(days=days))
    out = []
    for a in store.actors():
        for s in sessionize(store.events(a["SK"], since)):
            if s["actor_type"] == "service" and not include_services:
                continue
            out.append({k: v for k, v in s.items() if k != "timeline"})
    return sorted(out, key=lambda s: s["start"], reverse=True)


def actor_from_arn(arn: str) -> str | None:
    """Caller ARN (from the function URL's IAM auth) -> actor key.
    arn:aws:sts::1:assumed-role/Role/Session -> role/Role/Session; arn:aws:iam::1:user/u -> user/u."""
    resource = arn.split(":", 5)[-1] if arn.count(":") >= 5 else ""
    if resource.startswith("assumed-role/"):
        return "role/" + resource.removeprefix("assumed-role/")
    if resource.startswith("user/"):
        return "user/" + resource.rsplit("/", 1)[-1]
    if resource == "root":
        return "root"
    return None


def latest_session_id(actor: str, days: int = 7) -> str:
    since = _iso(datetime.now(timezone.utc) - timedelta(days=days))
    found = sessionize(store.events(actor, since))
    if not found:
        raise LookupError(f"no recorded activity for {actor} in the last {days} days")
    return found[-1]["session_id"]


def resolve(session_id: str | None, caller_arn: str | None = None) -> str:
    """'me' (or nothing) means the caller's latest session: an agent reviewing its own work."""
    if session_id and session_id != "me":
        return session_id
    actor = actor_from_arn(caller_arn or "")
    if not actor:
        raise ValueError("no session id and the caller's identity is unknown")
    return latest_session_id(actor)


def what_happened(session_id: str) -> dict:
    return answers.what_happened(*_session_items(session_id))


def risky_calls(session_id: str) -> dict:
    return answers.risky_calls(*_session_items(session_id))


def _session_items(session_id: str) -> tuple[dict, list[dict]]:
    actor, start = split_id(session_id)
    end = _iso(parse_time(start) + WINDOW)
    items = store.events(actor, start, end)
    for s in sessionize(items):
        if s["start"] == start:
            return s, [i for i in items if s["start"] <= i["time"] <= s["end"]]
    raise LookupError(f"no session {session_id}")


def session(session_id: str) -> dict:
    return _session_items(session_id)[0]


def _known_before(start: str) -> set:
    """Resources recorded as created before `start`, by anyone (for create-or-update calls)."""
    since = _iso(parse_time(start) - timedelta(days=90))
    keys = set()
    for a in store.actors():
        keys |= leftovers.created_keys([i for i in store.events(a["SK"], since, start) if i["time"] < start])
    return keys


def review(session_id: str, validate: bool = True) -> dict:
    s, items = _session_items(session_id)
    upserts = any(r.get("upsert") for i in items for r in i.get("creates", []))
    left = leftovers.analyze(items, aws_checks.cloud_control_check,
                             _known_before(s["start"]) if upserts else frozenset())
    g = guardrails.propose(items)
    if validate and g["agent_identity_policy"]:
        g["validation"] = {
            "agent_identity_policy": aws_checks.validate(g["agent_identity_policy"], "IDENTITY_POLICY"),
            "mcp_channel_policy_as_scp": aws_checks.validate(g["mcp_channel_policy"], "SERVICE_CONTROL_POLICY"),
        }
    return {
        "session": {k: v for k, v in s.items() if k != "timeline"},
        "left_running": left,
        "guardrails": g,
        "least_privilege": least_privilege(items, access_analyzer_status(session_id)),
    }


# --- IAM Access Analyzer policy generation, compared with the preview (D-027) -----------

def policy_actions(policy_json: str) -> set[str]:
    actions = set()
    for st in json.loads(policy_json).get("Statement", []):
        if st.get("Effect") == "Allow":
            a = st.get("Action", [])
            actions |= {a} if isinstance(a, str) else set(a)
    return actions


def least_privilege(items: list[dict], aa: dict) -> dict:
    """Preview + Access Analyzer + what each saw that the other didn't."""
    preview = guardrails.least_privilege_preview(items)
    out = {"preview": preview, "access_analyzer": aa}
    if aa.get("status") == "SUCCEEDED" and aa.get("policies"):
        listed = set().union(*(policy_actions(p) for p in aa["policies"]))
        # includeServiceLevelTemplate adds "<service>:<add-appropriate-actions>" placeholders
        theirs = {a for a in listed if "<" not in a}
        ours = set(preview["actions"])
        out["comparison"] = {"shared": len(ours & theirs),
                             "service_level_only": sorted({a.split(":")[0] for a in listed - theirs}
                                                          - {a.split(":")[0] for a in theirs}),
                             "only_chaperone": sorted(ours - theirs),
                             "only_access_analyzer": sorted(theirs - ours),
                             "missed_by_both_recovered": ["iam:PassRole"] if preview["passed_roles"] else []}
    return out


def _principal_arn(actor: str) -> str | None:
    if not actor.startswith("role/"):
        return f"arn:aws:iam::{os.environ.get('ACCOUNT_ID', '')}:{actor}" if actor.startswith("user/") else None
    import boto3
    return boto3.client("iam").get_role(RoleName=actor.split("/")[1])["Role"]["Arn"]


def access_analyzer_status(session_id: str) -> dict:
    job = store.table().get_item(Key={"PK": f"AAJOB#{session_id}", "SK": "JOB"}).get("Item")
    if not job:
        return {"status": "NOT_STARTED"}
    result = aws_checks.get_generated_policy(job["job_id"])
    return {"job_id": job["job_id"], "started_at": job["started_at"], **result}


def start_access_analyzer(session_id: str) -> dict:
    existing = store.table().get_item(Key={"PK": f"AAJOB#{session_id}", "SK": "JOB"}).get("Item")
    if existing:
        return access_analyzer_status(session_id)
    s = session(session_id)
    principal = _principal_arn(s["actor"])
    if not principal:
        return {"status": "UNSUPPORTED", "reason": f"{s['actor']} is not an IAM role or user"}
    # Pad the window: CloudTrail timestamps are per second and the last event may land late.
    start, end = parse_time(s["start"]) - timedelta(minutes=1), parse_time(s["end"]) + timedelta(minutes=5)
    job_id = aws_checks.start_policy_generation(principal, start, end)
    store.table().put_item(Item={"PK": f"AAJOB#{session_id}", "SK": "JOB", "job_id": job_id,
                                 "started_at": _iso(datetime.now(timezone.utc)), "principal": principal})
    return {"status": "IN_PROGRESS", "job_id": job_id, "principal": principal}
