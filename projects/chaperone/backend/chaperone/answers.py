"""Compact answers to the three questions, sized for an agent's context (D-028).

The session timeline can hold thousands of items; the MCP server and the chat get these
instead. Pure functions over one session's items, no AWS calls.

    what_happened(session, items)  what the actor did: tool calls, changes, resources
    risky_calls(session, items)    calls above plain writes, grouped by risk class, with
                                   "on something this session created" as context
"""

from __future__ import annotations

import json
import re

from . import rules
from .model import API, TOOL, parse_time

MAX_TOOL_CALLS = 40
MAX_CHANGES = 60
MAX_RISKY = 40

# Request parameters that name the resource a call acts on, most specific first.
TARGET_KEYS = ("functionName", "roleName", "policyArn", "bucketName", "tableName", "trailName", "name",
               "logGroupName", "queueUrl", "topicArn", "stackName", "clusterName", "instanceId",
               "instancesSet", "distributionId", "id", "certificateArn", "keyId", "userName", "Rule", "rule")


def _target(item: dict) -> str | None:
    for ref in item.get("creates", []) + item.get("deletes", []):
        return ref["id"]
    if item.get("resources"):
        return item["resources"][0]
    raw = item.get("params") or "{}"
    try:
        params = json.loads(raw)
    except ValueError:  # cut at PARAMS_MAX_BYTES: look for the key in the text
        for k in TARGET_KEYS:
            m = re.search(rf'"{k}":"([^"]+)"', raw)
            if m:
                return m.group(1)
        return None
    for k in TARGET_KEYS:
        v = params.get(k)
        if isinstance(v, str) and v:
            return v
    return None


def _tool_by_request(items: list[dict]) -> dict[str, str]:
    return {d["request_id"]: t.get("tool") for t in items if t["kind"] == TOOL
            for d in t.get("downstream", []) if d.get("request_id")}


def _call(item: dict, tools: dict) -> dict:
    out = {"time": item["time"], "action": f"{item['service']}:{item['action']}", "target": _target(item),
           "region": item.get("region"), "via": item.get("via")}
    tool = tools.get(item.get("request_id"))
    if tool:
        out["tool"] = tool
    if item.get("error_code"):
        out["error"] = item["error_code"]
    return out


def _collapse(calls: list[dict], limit: int) -> tuple[list[dict], int]:
    """Repeats of the same action on the same target (Terraform plans re-read everything)
    become one row with a count, first and last time."""
    rows: dict[tuple, dict] = {}
    for c in calls:
        key = (c["action"], c.get("target"), c.get("error"))
        if key in rows:
            rows[key]["count"] += 1
            rows[key]["last"] = c["time"]
        else:
            rows[key] = {**c, "count": 1}
    out = list(rows.values())
    return out[:limit], max(0, len(out) - limit)


def header(s: dict) -> dict:
    minutes = (parse_time(s["end"]) - parse_time(s["start"])).total_seconds() / 60
    return {"session_id": s["session_id"], "actor": s["actor"], "agent": s["agent"],
            "start": s["start"], "end": s["end"], "minutes": round(minutes, 1),
            "channels": s.get("operated_by", {}), "tool_calls": s["tool_calls"], "api_calls": s["api_calls"],
            "denied": s["denied"], "errors": s["errors"], "risk": s["risk"], "risk_counts": s["risk_counts"],
            "flags": s.get("flags", [])}


def what_happened(s: dict, items: list[dict]) -> dict:
    tools = _tool_by_request(items)
    tool_calls = []
    for t in (i for i in s["timeline"] if i["kind"] == TOOL):
        apis = sorted({c.get("api") or f"{c.get('service')}:{c.get('action')}" for c in t.get("calls", [])})
        tool_calls.append({"time": t["time"], "tool": t.get("tool"), "api_calls": len(t.get("calls", [])),
                           "apis": apis[:8], "risk": t["risk"]})
    writes = [_call(i, tools) for i in items if i["kind"] == API and i["risk"] != rules.READ]
    changes, more = _collapse(writes, MAX_CHANGES)
    created = [{"type": r["type"], "id": r["id"], "at": i["time"]}
               for i in items if i["kind"] == API for r in i.get("creates", [])]
    deleted = [{"type": r["type"], "id": r["id"], "at": i["time"]}
               for i in items if i["kind"] == API for r in i.get("deletes", [])]
    reads = sum(1 for i in items if i["kind"] == API and i["risk"] == rules.READ)
    return {
        "session": header(s),
        "reads": reads,
        "tool_calls": tool_calls[-MAX_TOOL_CALLS:],
        "tool_calls_omitted": max(0, len(tool_calls) - MAX_TOOL_CALLS),
        "changes": changes,
        "changes_omitted": more,
        "created": created,
        "deleted": deleted,
    }


def risky_calls(s: dict, items: list[dict]) -> dict:
    tools = _tool_by_request(items)
    own = {r["id"] for i in items if i["kind"] == API for r in i.get("creates", [])}
    by_class: dict[str, list[dict]] = {}
    for i in items:
        if i["kind"] != API or rules.SEVERITY.get(i["risk"], 0) < rules.SEVERITY[rules.DESTRUCTIVE]:
            continue
        c = _call(i, tools)
        c["reasons"] = i.get("reasons", [])
        t = c.get("target") or ""
        # Context for the reviewer, not a lower risk class: deleting the queue it just made,
        # or putting a policy on the role it just built.
        c["on_resource_created_this_session"] = bool(t) and any(t == o or t.endswith(f"/{o}") or
                                                                 t.endswith(f":{o}") for o in own)
        by_class.setdefault(i["risk"], []).append(c)
    classes = sorted(by_class, key=lambda r: (-rules.SEVERITY[r], r))
    out = {}
    for r in classes:
        rows, more = _collapse(by_class[r], MAX_RISKY)
        out[r] = {"calls": rows, "omitted": more}
    return {"session": header(s), "risky": out,
            "summary": {r: len(by_class[r]) for r in classes}}
