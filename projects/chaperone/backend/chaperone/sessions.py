"""Group one actor's items into sessions, at read time (D-020).

A session is a run of activity with no gap longer than IDLE_GAP. A burst of Identity
Center sign-ins (the proxy fetches fresh credentials for nearly every tool call) is
folded into one `signins` count instead of dozens of rows.
"""

from __future__ import annotations

from datetime import timedelta

from . import rules
from .model import API, SIGNIN, TOOL, parse_time

IDLE_GAP = timedelta(minutes=30)


def sessionize(items: list[dict], gap: timedelta = IDLE_GAP) -> list[dict]:
    """Items of one actor (any order) -> sessions, oldest first."""
    ordered = sorted(items, key=lambda i: (i["time"], i["SK"]))
    sessions: list[list[dict]] = []
    last = None
    for item in ordered:
        t = parse_time(item["time"])
        if last is None or t - last > gap:
            sessions.append([])
        sessions[-1].append(item)
        last = t
    return [summarize(s) for s in sessions]


def summarize(items: list[dict]) -> dict:
    """One session: its identity, time span, counts, riskiest verdict, and a timeline
    in which each tool call carries the API calls it made (joined on request ID)."""
    first, last = items[0], items[-1]
    tools = [i for i in items if i["kind"] == TOOL]
    apis = [i for i in items if i["kind"] == API]
    signins = [i for i in items if i["kind"] == SIGNIN]

    by_request = {a["request_id"]: a for a in apis if a.get("request_id")}
    claimed = set()
    timeline = []
    for item in items:
        if item["kind"] == SIGNIN:
            continue
        if item["kind"] == TOOL:
            calls = []
            verdicts = []
            for d in item.get("downstream", []):
                api = by_request.get(d.get("request_id"))
                if api:
                    claimed.add(api["request_id"])
                    calls.append(api)
                    verdicts.append(rules.Verdict(api["risk"], api.get("reasons", [])))
                else:
                    # Not in the trail (e.g. an S3 data event) or not ingested yet.
                    calls.append({"kind": "UNSEEN", "api": d.get("api"), "request_id": d.get("request_id"),
                                  "region": d.get("region"), "risk": d.get("risk")})
                    verdicts.append(rules.Verdict(d.get("risk") or rules.READ))
            top = rules.worst(verdicts)
            timeline.append({**item, "calls": calls, "risk": top.risk, "reasons": top.reasons})
        else:
            timeline.append(item)
    # API calls that belong to a tool call are shown under it, not twice.
    timeline = [t for t in timeline if not (t["kind"] == API and t.get("request_id") in claimed)]

    risk_counts: dict[str, int] = {}
    for a in apis:
        risk_counts[a["risk"]] = risk_counts.get(a["risk"], 0) + 1
    top = rules.worst(rules.Verdict(t["risk"], t.get("reasons", [])) for t in timeline)

    operated: dict[str, int] = {}
    for i in items:
        if i["kind"] != SIGNIN:
            operated[i.get("operated_by", "?")] = operated.get(i.get("operated_by", "?"), 0) + 1
    flags = sorted({f for i in items for f in i.get("flags", [])})

    return {
        "session_id": f"{first['actor']}@{first['time']}",
        "actor": first["actor"],
        "actor_type": first.get("actor_type"),
        "agent": any(i.get("agent") for i in items),
        "operated_by": operated,
        "flags": flags,
        "start": first["time"],
        "end": last["time"],
        "tool_calls": len(tools),
        "api_calls": len(apis),
        "signins": len(signins),
        "denied": sum(1 for i in items if i.get("error_class") == "denied"),
        "errors": sum(1 for i in items if i.get("error_class") == "other"),
        "risk": top.risk,
        "reasons": top.reasons,
        "risk_counts": risk_counts,
        "timeline": timeline,
    }
