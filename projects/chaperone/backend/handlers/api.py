"""HTTP API (Lambda function URL): the query layer as JSON.

    GET /api/sessions?days=7[&services=1]
    GET /api/session?id=<actor@start>
    GET /api/review?id=<actor@start>
    GET /api/least-privilege?id=<actor@start>[&start=1]   (IAM Access Analyzer job)
    GET /api/what-happened?id=<actor@start>                 compact answers for agents (D-028)
    GET /api/risky?id=<actor@start>

`id=me` (or no id, on the per-session routes) is the caller's latest session, from the
function URL's IAM auth: an agent reviewing its own work through the MCP server.
"""

import json
import logging
from decimal import Decimal

from chaperone import query

log = logging.getLogger()
log.setLevel(logging.INFO)


def _json(o):
    if isinstance(o, Decimal):
        return int(o) if o == int(o) else float(o)
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    return str(o)


def _reply(status, body):
    return {"statusCode": status, "headers": {"content-type": "application/json", "cache-control": "no-store"},
            "body": json.dumps(body, default=_json)}


def _caller(event) -> str | None:
    return (((event.get("requestContext") or {}).get("authorizer") or {}).get("iam") or {}).get("userArn")


def handler(event, _context):
    path = (event.get("rawPath") or "/").rstrip("/")
    q = event.get("queryStringParameters") or {}
    try:
        if path.endswith("/api/sessions"):
            return _reply(200, query.sessions(int(q.get("days", 7)), q.get("services") == "1"))
        sid = query.resolve(q.get("id"), _caller(event))
        if path.endswith("/api/session"):
            return _reply(200, query.session(sid))
        if path.endswith("/api/review"):
            return _reply(200, query.review(sid))
        if path.endswith("/api/what-happened"):
            return _reply(200, query.what_happened(sid))
        if path.endswith("/api/risky"):
            return _reply(200, query.risky_calls(sid))
        if path.endswith("/api/least-privilege"):
            if q.get("start") == "1":
                return _reply(202, query.start_access_analyzer(sid))
            return _reply(200, {"session_id": sid, **query.least_privilege(query._session_items(sid)[1],
                                                                           query.access_analyzer_status(sid))})
        return _reply(404, {"error": "not found"})
    except KeyError as e:
        return _reply(400, {"error": f"missing parameter {e}"})
    except (LookupError, ValueError) as e:
        return _reply(404, {"error": str(e)})
    except Exception:
        log.exception("api error")
        return _reply(500, {"error": "internal error"})
