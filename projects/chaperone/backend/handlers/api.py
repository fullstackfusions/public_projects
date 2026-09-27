"""HTTP API (Lambda function URL): the query layer as JSON.

    GET /api/sessions?days=7[&services=1]
    GET /api/session?id=<actor@start>
    GET /api/review?id=<actor@start>
    GET /api/least-privilege?id=<actor@start>[&start=1]   (IAM Access Analyzer job)
    GET /api/what-happened?id=<actor@start>                 compact answers for agents (D-028)
    GET /api/risky?id=<actor@start>
    GET /api/replay?id=<actor@start>                        slim timeline for the site
    GET /api/event?id=<actor@start>&event=<event ID>        one raw event (masked in public)
    GET /api/explain?id=<actor@start>[&generate=1]          stored plain-English explanation
                                                            (generate=1 calls Bedrock, D-029)

`id=me` (or no id, on the per-session routes) is the caller's latest session, from the
function URL's IAM auth: an agent reviewing its own work through the MCP server.

Requests through CloudFront carry `x-chaperone-view: public` (D-031): identifiers are
masked, `id=me`, `start=1` and `generate=1` are refused, and answers may be cached at the edge.
"""

import json
import logging
import os
from decimal import Decimal

from chaperone import explain, public, query, store

log = logging.getLogger()
log.setLevel(logging.INFO)


def _json(o):
    if isinstance(o, Decimal):
        return int(o) if o == int(o) else float(o)
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    return str(o)


SESSION_ROUTES = {"/api/session", "/api/replay", "/api/event", "/api/review", "/api/what-happened",
                  "/api/risky", "/api/least-privilege", "/api/explain"}
PUBLIC_DAYS = 60  # the site keeps showing the hackathon's sessions through judging
PUBLIC_MAX_AGE = {"/api/sessions": 60}  # seconds at the edge; per-session answers get 300


def _reply(status, body, public_view=False, path=""):
    if not public_view:
        return {"statusCode": status, "headers": {"content-type": "application/json", "cache-control": "no-store"},
                "body": json.dumps(body, default=_json)}
    age = PUBLIC_MAX_AGE.get(path, 300) if status == 200 else 10
    return {"statusCode": status, "headers": {"content-type": "application/json",
                                              "cache-control": f"public, max-age={age}"},
            "body": public.mask(body, os.environ.get("ACCOUNT_ID", ""), default=_json)}


def _caller(event) -> str | None:
    return (((event.get("requestContext") or {}).get("authorizer") or {}).get("iam") or {}).get("userArn")


def _is_public(event) -> bool:
    return ((event.get("headers") or {}).get("x-chaperone-view") or "").lower() == "public"


def _public_id(q) -> str:
    sid = q.get("id") or ""
    if not sid or sid == "me":
        raise PermissionError("the public view needs a session id")
    return public.unmask_session_id(sid, [a["SK"] for a in store.actors()], os.environ.get("ACCOUNT_ID", ""))


def handler(event, _context):
    path = (event.get("rawPath") or "/").rstrip("/")
    q = event.get("queryStringParameters") or {}
    pub = _is_public(event)
    route = path[path.find("/api/"):] if "/api/" in path else path

    def reply(status, body):
        return _reply(status, body, pub, route)

    try:
        if route == "/api/sessions":
            days = min(int(q.get("days", PUBLIC_DAYS if pub else 7)), PUBLIC_DAYS if pub else 90)
            return reply(200, explain.with_headlines(query.sessions(days, q.get("services") == "1" and not pub)))
        if route not in SESSION_ROUTES:
            return reply(404, {"error": "not found"})
        sid = _public_id(q) if pub else query.resolve(q.get("id"), _caller(event))
        if route == "/api/session" and not pub:
            return reply(200, query.session(sid))
        if route == "/api/replay":
            return reply(200, public.replay(query.session(sid)))
        if route == "/api/event":
            return reply(200, public.find_event(query.session(sid), q["event"]))
        if route == "/api/review":
            return reply(200, query.review(sid))
        if route == "/api/what-happened":
            return reply(200, query.what_happened(sid))
        if route == "/api/risky":
            return reply(200, query.risky_calls(sid))
        if route == "/api/explain":
            if q.get("generate") == "1":
                if pub:
                    raise PermissionError("the public view can't start model calls")
                return reply(200, explain.generate(sid))
            return reply(200, explain.get(sid))
        if route == "/api/least-privilege":
            if q.get("start") == "1":
                if pub:
                    raise PermissionError("the public view can't start jobs")
                return reply(202, query.start_access_analyzer(sid))
            return reply(200, {"session_id": sid, **query.least_privilege(query._session_items(sid)[1],
                                                                          query.access_analyzer_status(sid))})
        return reply(404, {"error": "not found"})
    except PermissionError as e:
        return reply(403, {"error": str(e)})
    except KeyError as e:
        return reply(400, {"error": f"missing parameter {e}"})
    except (LookupError, ValueError) as e:
        return reply(404, {"error": str(e)})
    except Exception:
        log.exception("api error")
        return reply(500, {"error": "internal error"})
