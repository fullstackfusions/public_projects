# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=2.2,<3", "boto3>=1.35"]
# ///
"""Chaperone MCP server: ask what an agent did in your AWS account, from inside the agent.

A thin stdio client over Chaperone's query API (D-028). Requests are signed with SigV4 by
whatever AWS credentials the environment has, so the only permission needed is
`lambda:InvokeFunctionUrl` on the API function, and "me" means the caller's own latest
session: an agent can review its own AWS work before it says it's done.

    CHAPERONE_API_URL   the API's function URL (terraform output api_url)
    AWS_PROFILE         optional; any credentials that can invoke the URL
    AWS_REGION          the API's region (default us-east-1)

Run: uv run --script server.py
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import BotoCoreError, ClientError
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

API_URL = os.environ.get("CHAPERONE_API_URL", "").rstrip("/")
REGION = os.environ.get("AWS_REGION", "us-east-1")

mcp = MCPServer("chaperone", instructions=(
    "Chaperone records every AWS API call made by AI agents and people in this AWS account "
    "(from CloudTrail), groups them into sessions, and classifies risk with deterministic rules. "
    "Use it to review your own AWS work before finishing a task: session_id 'me' is your own "
    "latest session. New events take a few minutes to arrive (CloudTrail delivery)."))

_session = boto3.Session()
READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)


def _get(path: str, **params) -> dict | list:
    """GET the API, SigV4-signed. Failures become ToolErrors so the model reads the reason."""
    if not API_URL:
        raise ToolError("CHAPERONE_API_URL is not set in the MCP server's environment")
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{API_URL}{path}" + (f"?{query}" if query else "")
    req = AWSRequest(method="GET", url=url)
    try:
        creds = _session.get_credentials()
        if creds is None:
            raise ToolError("no AWS credentials; set AWS_PROFILE for the MCP server")
        SigV4Auth(creds.get_frozen_credentials(), "lambda", REGION).add_auth(req)
    except (BotoCoreError, ClientError) as e:  # e.g. an expired SSO token
        raise ToolError(f"AWS credentials: {e}. For SSO profiles run `aws sso login`.") from None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=dict(req.headers)), timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            message = json.loads(body).get("error", body)
        except ValueError:
            message = body
        raise ToolError(f"Chaperone API {e.code}: {message}") from None
    except urllib.error.URLError as e:
        raise ToolError(f"Chaperone API unreachable: {e.reason}") from None


@mcp.tool(annotations=READ)
def list_sessions(days: int = 7, agents_only: bool = False) -> list[dict]:
    """Recorded sessions in this AWS account, newest first. A session is one actor's run of
    activity (an agent's role session or a person's sign-in) with no gap over 30 minutes.
    Each row: session_id, actor, whether it was an agent, time span, tool/API call counts,
    and its riskiest class (read < write < destructive < public_exposure |
    identity_escalation | audit_tampering)."""
    keep = ("session_id", "actor", "agent", "start", "end", "tool_calls", "api_calls", "denied", "risk",
            "risk_counts", "flags")
    rows = [{k: s.get(k) for k in keep} for s in _get("/api/sessions", days=days)]
    return [r for r in rows if r["agent"]] if agents_only else rows


@mcp.tool(annotations=READ)
def what_did_the_agent_do(session_id: str = "me") -> dict:
    """What happened in one session: the MCP tool calls (each with the AWS APIs it made),
    every change (non-read call, repeats collapsed with a count), the resources it created
    and deleted, and which channel made them (MCP, Terraform, CLI, console).
    session_id: from list_sessions, or 'me' for your own latest session."""
    return _get("/api/what-happened", id=session_id)


@mcp.tool(annotations=READ)
def risky_calls(session_id: str = "me") -> dict:
    """The calls in one session above plain writes, grouped by risk class, with the rule's
    reasons and the tool call that made them. `on_resource_created_this_session` marks, for
    example, deleting a queue the session itself created: context for the reviewer, not a
    lower risk. session_id: from list_sessions, or 'me' for your own latest session."""
    return _get("/api/risky", id=session_id)


@mcp.tool(annotations=READ)
def review_session(session_id: str = "me") -> dict:
    """The reviewer's answers for one session: what it left running (checked live through
    the AWS Cloud Control API, with idle cost per month), and guardrails proposed from its
    risky calls as IAM deny statements (for the agent's identity, and for the MCP channel
    with aws:ViaAWSMCPService), each validated by IAM Access Analyzer.
    session_id: from list_sessions, or 'me' for your own latest session."""
    r = _get("/api/review", id=session_id)
    r.pop("least_privilege", None)  # its own tool
    return r


# Not read-only: start_access_analyzer starts an IAM Access Analyzer job.
@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
def least_privilege(session_id: str = "me", start_access_analyzer: bool = False) -> dict:
    """The IAM permissions this session actually used, as a policy: Chaperone's instant
    preview (includes iam:PassRole recovered from requests, which CloudTrail never logs),
    IAM Access Analyzer's generated policy when a job exists, and what each saw that the
    other didn't. start_access_analyzer=true starts a policy generation job (takes a few
    minutes; call again later for the result).
    session_id: from list_sessions, or 'me' for your own latest session."""
    if start_access_analyzer:
        return _get("/api/least-privilege", id=session_id, start="1")
    r = _get("/api/least-privilege", id=session_id)
    for k in ("actions", "by_service"):  # both repeat what the policy lists
        r.get("preview", {}).pop(k, None)
    return r


def main():
    mcp.run()


if __name__ == "__main__":
    main()
