"""Plain-English explanation of one session, generated once with Bedrock and stored (D-029).

Visitors read the stored text; nothing a visitor does calls a model. The model sees the
same compact answers the MCP server returns (answers.py), never the raw timeline, and is
told to describe only what the record shows.

    build_input(session, items)  the facts the model gets (pure)
    generate(session_id)         call Bedrock, store, return the explanation
    get(session_id)              the stored explanation, marked stale if the session grew
    with_headlines(sessions)     headlines for the session list

Stored as  EXPLAIN#<session_id> / v1  with the session's end and call counts at the time
(`basis`), so a session that kept going after its explanation was written shows as stale.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from . import answers, guardrails, store

MODEL_ID = os.environ.get("EXPLAIN_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
VERSION = "v1"
MAX_TOKENS = 1500

SYSTEM = """You explain one recorded session of AWS activity to a reader who was not there: \
an engineer or manager checking what an AI coding agent (or a person) did in their AWS account.

You get a JSON record built from CloudTrail by Chaperone: the session header, the MCP tool \
calls, every change (repeats collapsed with a count), resources created and deleted, calls \
classed above a plain write (destructive, public exposure, identity escalation, audit \
tampering) with the rule's reasons, and how many IAM actions the session actually used \
against what its identity was granted.

Rules:
- Describe only what the record shows. Do not guess intent, and say so when the record \
cannot tell (for example why something was deleted).
- Name services and resources the way an engineer would ("an S3 bucket for Terraform state"), \
not as raw API names, except where the exact call matters.
- For risky calls, say whether they acted on something this same session created: deleting \
your own test queue is not the same as deleting someone else's.
- Numbers: take counts from the record as they are. `risky_counts` is the exact number of \
risky calls per class; a row in `risky` with "count" stands for that many calls. If you \
describe only some of them, say which part ("four of the six").
- Channels in `session.channels` (Terraform, AWS CLI, the AWS MCP server, ...) are recorded \
facts: state them plainly, never "Terraform-style".
- `least_privilege.granted` is what the identity was allowed. If it is null, say how many \
actions were used and do not say what was allowed.
- Use ASCII hyphens in names.
- Never write account IDs, access keys, IP addresses or email addresses.
- Plain, calm, specific. No marketing words, no exclamation marks.

Answer with JSON only, no code fence:
{"headline": "<one sentence, at most 20 words>",
 "summary": "<3 to 5 sentences: what was built or changed, through which channels, how it ended>",
 "moments": [{"time": "<ISO time from the record>", "text": "<one sentence>"}],
 "risk": "<2 to 4 sentences on the risky calls and what they touched, or why there were none>",
 "access": "<1 to 2 sentences: actions used versus what the role allowed>"}
Give 3 to 6 moments, in time order."""


def build_input(s: dict, items: list[dict]) -> dict:
    what = answers.what_happened(s, items)
    risky = answers.risky_calls(s, items)
    lp = guardrails.least_privilege_preview(items)
    return {"session": what["session"], "reads": what["reads"],
            "tool_calls": what["tool_calls"], "tool_calls_omitted": what["tool_calls_omitted"],
            "changes": what["changes"], "changes_omitted": what["changes_omitted"],
            "created": what["created"], "deleted": what["deleted"],
            "risky": risky["risky"], "risky_counts": risky["summary"],
            "least_privilege": {"granted": granted(s["actor"]), "actions_used": len(lp["actions"]),
                                "services": sorted({a.split(":")[0] for a in lp["actions"]}),
                                "passed_roles": len(lp["passed_roles"])}}


def granted(actor: str) -> str | None:
    """What the identity was allowed, where Chaperone knows it. Same rule as the console's
    least-privilege panel: this account's Identity Center permission sets grant
    AdministratorAccess (Action "*")."""
    if "AWSReservedSSO_" in actor:
        return 'AdministratorAccess through an Identity Center permission set ("Action": "*")'
    return None


def basis(s: dict) -> dict:
    return {"end": s["end"], "api_calls": s["api_calls"], "tool_calls": s["tool_calls"]}


def _parse(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    out = _ascii_hyphens(json.loads(text))
    missing = {"headline", "summary", "moments", "risk", "access"} - out.keys()
    if missing:
        raise ValueError(f"explanation missing {sorted(missing)}")
    return out


def _ascii_hyphens(v):
    """Some models write names with non-breaking hyphens (U+2011); names must match when copied."""
    if isinstance(v, str):
        return v.replace("\u2011", "-").replace("\u2010", "-")
    if isinstance(v, dict):
        return {k: _ascii_hyphens(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_ascii_hyphens(x) for x in v]
    return v


def call_model(facts: dict, client=None) -> tuple[dict, dict]:
    import boto3
    client = client or boto3.client("bedrock-runtime")
    r = client.converse(modelId=MODEL_ID, system=[{"text": SYSTEM}],
                        messages=[{"role": "user", "content": [{"text": json.dumps(facts, default=str)}]}],
                        inferenceConfig={"maxTokens": MAX_TOKENS})
    text = "".join(c.get("text", "") for c in r["output"]["message"]["content"])
    return _parse(text), r.get("usage", {})


def generate(session_id: str, client=None) -> dict:
    from .query import _session_items
    s, items = _session_items(session_id)
    explanation, usage = call_model(build_input(s, items), client)
    item = {"PK": f"EXPLAIN#{session_id}", "SK": VERSION, "model": MODEL_ID, "basis": basis(s),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "explanation": explanation,
            "usage": {k: usage.get(k, 0) for k in ("inputTokens", "outputTokens")}}
    store.table().put_item(Item=item)
    return _view(item, s)


def get(session_id: str) -> dict:
    from .query import session
    item = store.table().get_item(Key={"PK": f"EXPLAIN#{session_id}", "SK": VERSION}).get("Item")
    if not item:
        return {"session_id": session_id, "status": "NOT_GENERATED"}
    return _view(item, session(session_id))


def with_headlines(sessions: list[dict]) -> list[dict]:
    """Add each session's explanation headline (if written) for the overview: one batch read."""
    found = {i["PK"].removeprefix("EXPLAIN#"): i for i in store.get_many(
        [{"PK": f"EXPLAIN#{s['session_id']}", "SK": VERSION} for s in sessions])}
    for s in sessions:
        item = found.get(s["session_id"])
        if item:
            s["headline"] = item["explanation"]["headline"]
    return sessions


def _view(item: dict, s: dict) -> dict:
    return {"session_id": s["session_id"], "status": "STALE" if item["basis"] != basis(s) else "READY",
            "model": item["model"], "generated_at": item["generated_at"], **item["explanation"]}
