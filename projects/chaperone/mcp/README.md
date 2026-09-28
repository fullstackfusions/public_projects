# Chaperone MCP server

Ask Chaperone about your AWS account from inside the agent: what a session did, what was risky, what it left running, and the access it needed. `session_id="me"` is the caller's own latest session, so an agent can review its own AWS work before saying it's done.

| Tool | Answers |
|---|---|
| `list_sessions` | Recorded sessions (agents and people), newest first, with riskiest class |
| `what_did_the_agent_do` | MCP tool calls with the AWS APIs each made, every change, resources created and deleted, by channel |
| `risky_calls` | Calls above plain writes by risk class, with rule reasons and "on something this session created" |
| `review_session` | Left running (Cloud Control check, idle cost) and guardrails as IAM denies, validated by IAM Access Analyzer |
| `least_privilege` | The policy the session needed (with `iam:PassRole` recovered), IAM Access Analyzer's version, and the differences |

## How it works

A stdio server that calls Chaperone's API (a Lambda function URL with IAM auth), signing each request with SigV4 using whatever AWS credentials it runs with. The only permission it needs is `lambda:InvokeFunctionUrl` on that function; it never reads DynamoDB or CloudTrail itself. Function URL invocations are data events, so looking at a session doesn't add to it.

## Install (Claude Code)

Needs [uv](https://docs.astral.sh/uv/) (dependencies are declared inline in `server.py`).

```bash
claude mcp add chaperone \
  -e CHAPERONE_API_URL=https://<function-url>.lambda-url.us-east-1.on.aws/ \
  -e AWS_PROFILE=<profile> \
  -- uv run --quiet --script /path/to/chaperone/mcp/server.py
```

`CHAPERONE_API_URL` is `terraform output api_url` in `infra/live`. It's a standard stdio MCP server, so any MCP-capable agent can run it with the same command and environment; we have run it with Claude Code.

## Recording a demo

Set `CHAPERONE_MASK_ACCOUNT=<account ID>` in the server's environment and its answers are masked the way the public site masks them (account ID, role suffixes, identity IDs, IP addresses). The public view itself can't be used for this, because it refuses session `"me"`.

## Check it

```bash
CHAPERONE_API_URL=... AWS_PROFILE=... uv run --script smoke_test.py
```

## Related

- [Chaperone](../README.md)
- [Chaperone — hackathon journey](../journey/_index.md)
