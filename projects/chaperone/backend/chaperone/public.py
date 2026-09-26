"""The public view: what the live site may show (D-031).

Every request that comes through CloudFront carries `x-chaperone-view: public` (an origin
custom header; CloudFront overwrites any viewer copy of it). In that view the API:

- masks identifiers: account ID (plain and base64, gotcha #16), the Identity Center role
  suffix and directory ID, the identity store user IDs, IP addresses, access key IDs,
  session tokens, emails, CloudFront distribution and function URL IDs;
- drops fields a visitor has no use for (request IDs, `on_behalf_of`, table keys);
- serves the timeline as a slim replay (the full one is 4 MB for a long session), with the
  raw event for one call on request;
- refuses `id=me` and anything that starts work (Access Analyzer jobs).

Masking is applied to the finished JSON text, so a field added later can't slip past it.
"""

from __future__ import annotations

import base64
import json
import re

from .model import API, TOOL

MASKED_ACCOUNT = "111122223333"
DROP_KEYS = {"PK", "SK", "request_id", "on_behalf_of", "expires_at", "account"}

_PATTERNS = [
    (re.compile(r"(AWSReservedSSO_[A-Za-z0-9+=,.@-]+?)_[0-9a-f]{16}"), r"\1_0000000000000000"),
    (re.compile(r"\bd-[0-9a-f]{10}\b"), "d-0000000000"),
    (re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), "ASIAXXXXXXXXEXAMPLE0"),
    (re.compile(r"\b[a-z0-9]{32}(\.lambda-url\.)"), r"00000000000000000000000000000000\1"),
    (re.compile(r"\bE[0-9A-Z]{12,13}\b"), "EDFDVBD6EXAMPLE"),
    (re.compile(r"[A-Za-z0-9+/]{120,}={0,2}"), "[redacted]"),  # session tokens, SAML assertions
    (re.compile(r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b"), "192.0.2.0"),
    (re.compile(r"\b[0-9a-f]{1,4}(?::[0-9a-f]{0,4}){4,7}\b", re.I), "2001:db8::"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"), "user@example.com"),
]


def _base64_cores(value: str) -> list[str]:
    """The part of base64(value) that doesn't depend on its neighbours, at all 3 alignments."""
    cores = []
    for pad in range(3):
        enc = base64.b64encode(b"\0" * pad + value.encode()).decode()
        start = -(-pad * 4 // 3)  # characters touched by the padding
        cores.append(enc[start + 1:-3])
    return [c for c in cores if len(c) >= 8]


def mask_text(text: str, account_id: str = "", secrets: tuple[str, ...] = ()) -> str:
    for s in secrets:
        if s:
            text = text.replace(s, "00000000-0000-0000-0000-000000000000")
    if account_id:
        text = text.replace(account_id, MASKED_ACCOUNT)
        for core in _base64_cores(account_id):
            text = text.replace(core, "[redacted]")
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text


def _strip(o):
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if k not in DROP_KEYS}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


def _identity_ids(o, found: set) -> set:
    """Identity store user IDs (`on_behalf_of`) anywhere in the body: masked everywhere."""
    if isinstance(o, dict):
        if isinstance(o.get("on_behalf_of"), str):
            found.add(o["on_behalf_of"])
        for v in o.values():
            _identity_ids(v, found)
    elif isinstance(o, list):
        for v in o:
            _identity_ids(v, found)
    return found


def mask(body, account_id: str, default=str) -> str:
    """Body -> masked JSON text for the public view."""
    secrets = tuple(sorted(_identity_ids(body, set()), key=len, reverse=True))
    return mask_text(json.dumps(_strip(body), default=default), account_id, secrets)


def unmask_session_id(masked: str, actors: list[str], account_id: str = "") -> str:
    """A masked session ID from the site -> the real one, by masking each known actor."""
    actor, _, start = masked.rpartition("@")
    for a in actors:
        if mask_text(a, account_id) == actor:
            return f"{a}@{start}"
    return masked


# --- The slim replay: everything the flight path and the list need, nothing else ---------

def _api(item: dict) -> str:
    return item.get("api") or f"{item.get('service')}:{item.get('action')}"


def _mark(item: dict, target) -> dict:
    out = {"time": item.get("time"), "kind": item["kind"], "api": _api(item), "risk": item.get("risk"),
           "via": item.get("via"), "region": item.get("region"), "event_id": item.get("event_id")}
    if item.get("reasons"):
        out["reasons"] = item["reasons"]
    if item.get("error_class"):
        out["error"] = item["error_class"]
        out["error_code"] = item.get("error_code")
    t = target(item) if item["kind"] == API else None
    if t:
        out["target"] = t
    if item.get("creates"):
        out["creates"] = [r["id"] for r in item["creates"]]
    if item.get("deletes"):
        out["deletes"] = [r["id"] for r in item["deletes"]]
    if item.get("operated_by"):
        out["operated_by"] = item["operated_by"]
    return out


def replay(s: dict) -> dict:
    from .answers import _target  # one definition of "what a call acts on"

    marks = []
    for item in s["timeline"]:
        m = _mark(item, _target)
        if item["kind"] == TOOL:
            m["api"] = None
            m["tool"] = item.get("tool")
            m["calls"] = [_mark(c, _target) for c in item.get("calls", [])]
        marks.append(m)
    return {"session": {k: v for k, v in s.items() if k != "timeline"}, "marks": marks}


def find_event(s: dict, event_id: str) -> dict:
    for item in s["timeline"]:
        if item.get("event_id") == event_id:
            return {k: v for k, v in item.items() if k != "calls"} if item["kind"] == TOOL else item
        for c in item.get("calls", []):
            if c.get("event_id") == event_id:
                return c
    raise LookupError(f"no event {event_id} in this session")
