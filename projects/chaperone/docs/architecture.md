# Chaperone architecture

How Chaperone records what an AI coding agent did in an AWS account, how it attributes each AWS API call to the agent and the tool call that made it, and how it turns that record into a review. Numbers are measured in the build account and come from the [journey](../journey/_index.md).

## The problem

Coding agents (Claude Code, Kiro, Amazon Q Developer, Cursor) now act in AWS accounts through the AWS MCP Server, the AWS CLI and Terraform. CloudTrail records every call, but the raw record answers none of the questions a reviewer has after an agent session:

1. **What did the agent do?** Which calls came from the agent rather than a person, through which channel, and grouped under which of the agent's actions.
2. **Was anything risky?** Deletes, new access, public exposure, changes to the audit trail.
3. **What did it leave behind, and what access does it actually need?** Resources still running, guardrails that would not have broken the agent's real work, and a least-privilege policy.

Chaperone answers those three questions from CloudTrail, with deterministic rules (no model decides risk), using AWS's own services wherever one exists.

## How attribution works

The agent gets its own identity: an IAM Identity Center user with a permission set and 4-hour sessions ([D-007](../journey/decisions.md)). It never shares the human's identity and never holds a long-lived key. That one choice makes everything after it attributable.

One agent action through the AWS MCP Server appears in CloudTrail at three levels:

| Level | CloudTrail record | How Chaperone uses it |
|---|---|---|
| MCP tool call | `eventSource = aws-mcp.amazonaws.com`, `eventName = CallReadWriteTool`, `eventType = AwsMcpEvent`. The user agent names the client (`claude-code/<ver>`, `mcp-proxy-for-aws/<ver>`). `additionalEventData.downstreamRequests[]` lists each AWS API it called, with the request ID. Tool arguments are stored as `[HIDDEN_DUE_TO_SECURITY_REASONS]`. | A band on the session timeline |
| Downstream API call | The service's own event, with `userIdentity.invokedBy = aws-mcp.amazonaws.com` and a `requestID` that matches one of the tool call's `downstreamRequests` | Joined to its tool call by request ID, in either arrival order |
| Direct call | The same identity through the CLI, Terraform or an SDK, with its own user agent and source IP | On the same timeline, labelled with its channel |

Details that shaped the design:

- **Every MCP tool call is logged `readOnly: false`,** even `GetCallerIdentity`. Risk is judged from the downstream API calls, never from the tool call.
- **MCP reveals calls the trail doesn't record.** `s3:PutObject`, `dynamodb:Query` and `cloudwatch:GetMetricData` are data-level calls that a management-events trail never logs, but they appear in the tool call's `downstreamRequests`. They show on the timeline as "unseen" calls.
- **An agent is known by its identity, not its user agent.** On Day 1, 558 Terraform calls made by the agent carried a user agent that doesn't mention Claude Code. Sessions of roles whose name starts with a configured prefix (`AGENT_ROLE_PREFIXES`, default `AWSReservedSSO_ChaperoneAgent_`) are agent activity whatever tool made the call; the user agent only adds the channel ([D-021](../journey/decisions.md)).
- **MCP is a channel, not an actor** ([D-024](../journey/decisions.md)). Each event carries `actor_type` (human, agent, workload, service: who the identity is), `via` (mcp, console, cli, terraform, sdk, service:x: how) and `operated_by` (who drove it). An agent working through MCP on a person's identity is flagged `agent_on_human_identity`, the case a simple human/agent/MCP label would hide.
- **Sign-ins fold into one marker.** Identity Center issues role credentials each time the MCP proxy fetches them (about one `AssumeRoleWithSAML` per tool call, plus `sso:GetRoleCredentials` from the agent's tooling). They are filed under the role session they create and shown as a count.

## Ingest

```
CloudTrail (multi-region trail)
  ├─ API calls ──► EventBridge (us-east-1 default bus) ──► Lambda chaperone-ingest ──► DynamoDB
  │                  ▲ forwarding rules in the 16 other enabled regions
  └─ MCP tool calls, sign-ins ◄── LookupEvents ◄── Lambda chaperone-poller (every minute) ──► DynamoDB
                                                    + reconcile: each agent's activity, all regions
DynamoDB ──► Lambda chaperone-api (function URL, IAM auth) ──► MCP server · console
```

- **EventBridge does not deliver MCP tool-call events.** A probe rule matching every event from the agent (with read-only events included) received 6 `AwsApiCall` events in 4 minutes and no `AwsMcpEvent`, while `LookupEvents` showed both tool calls ([D-018](../journey/decisions.md)). So ingest is hybrid: EventBridge for API calls (stored ~1–30 s after the call), and a one-minute poller that reads `aws-mcp.amazonaws.com` events through `LookupEvents` (stored ~1.5 min after the call). The two are joined on request ID.
- **Every region.** CloudTrail delivers an event to EventBridge only in the region where it happened, so an `UpdateTrail` in the trail's home region (us-east-2) was invisible at first. Each other enabled region has a forwarding rule to the us-east-1 bus through a role that can only `events:PutEvents` there ([D-022](../journey/decisions.md)). Proof: a no-op `UpdateTrail` in us-east-2 and a `DescribeVpcs` in eu-west-1 were stored within ~27 s.
- **Read-only events** are included with the rule state `ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS`.
- **Reconcile.** EventBridge can skip events: 12 `kms:Decrypt` calls Lambda made for the agent never reached the rule. The poller re-reads each agent's activity with `LookupEvents` across all 17 regions, a fifth of them per run. Exact check for 18:34–18:43 on Day 1, all regions: agent 651/651, human 2/2, sign-ins 29/29. The only known gap is KMS crypto calls made by AWS services on their own.
- **Loop guard.** AWS services assuming Chaperone's own `chaperone-*` roles are excluded in the event pattern itself (forwarding them would generate more of them), checked with `TestEventPattern` on 8 cases before applying.
- **Backfill.** On install, the poller can load history from before Chaperone existed (`{"backfill_user": …, "lookback_minutes": …}`): 563 events on the first run.

## Data model

One DynamoDB table. Events are stored per actor and time; sessions are derived when reading, not stored ([D-020](../journey/decisions.md)). Every write is keyed by the CloudTrail event ID, so EventBridge, the poller and a backfill can write the same event in any order.

| Item | PK | SK | Key fields |
|---|---|---|---|
| API call | `ACTOR#<actor>` | `<time>#API#<eventID>` | service, action, region, request ID, readOnly, risk class and reasons, `via`, `actor_type`, `operated_by`, error class (`denied`, `not_found`, `other`), resources created or deleted, trimmed parameters |
| MCP tool call | `ACTOR#<actor>` | `<time>#TOOL#<eventID>` | tool name, downstream APIs with request IDs |
| Sign-in | `ACTOR#<actor>` | `<time>#SIGNIN#<eventID>` | `AssumeRoleWithSAML` / `GetRoleCredentials`, filed under the role session it creates |
| Actor | `ACTORS` | `<actor>` | last seen, agent flag |
| Identity Center user | `IDC#<userId>` | `ACTOR` | the role session that user acts as |
| Poller cursor | `POLLER#<name>` | `CURSOR` | event IDs already written in the look-back window |
| Access Analyzer job | `AAJOB#<session>` | `JOB` | policy generation job ID and start time |

- **Actor** = `role/<RoleName>/<SessionName>`, `user/<name>` or `root`.
- **Session** = a run of one actor's activity with no gap over 30 minutes. Tool calls claim their API calls by request ID.
- **Retention:** items expire after 90 days (TTL), matching CloudTrail event history; events of AWS services acting on their own after 7 days.
- **Capacity:** on-demand, capped at 100 read and 100 write units per second ([D-025](../journey/decisions.md)). With 10 provisioned WCU, a ~1,650-event backfill produced 2,755 write throttles; batch writes (25 per request) and the cap fixed it, and the cap bounds the worst-case bill.

Code: [`backend/chaperone/`](../backend/chaperone/) (`model.py`, `rules.py`, `sessions.py`, `store.py`, `query.py`, `answers.py`).

## Risk classes

Deterministic, pure functions with unit tests on real recorded events ([`rules.py`](../backend/chaperone/rules.py)). A model never decides risk.

| Class | What triggers it |
|---|---|
| `read` | `Get*`, `List*`, `Describe*`, `Lookup*`, `Query`, `Scan`, … |
| `write` | Creates and updates that match no class below |
| `destructive` | `Delete*`, `Terminate*`, `Purge*`, `Deregister*`, `Remove*` |
| `identity_escalation` | New access: `iam:Attach*Policy`, `iam:PutRolePolicy`, `iam:CreateAccessKey`, … |
| `public_exposure` | Read from the request payload, not guessed from the API name: bucket policies with Principal `*` and no condition, public access block removed or weakened, public ACLs, security groups open to `0.0.0.0/0` or `::/0`, Lambda URLs with `authType NONE`, public snapshots and AMIs, SQS/SNS policies |
| `audit_tampering` | `cloudtrail:StopLogging`, `DeleteTrail`, `UpdateTrail`, … |

The rules apply to people and agents alike: Mihir's own Day 0 console session, fixing the trail by hand, is flagged `audit_tampering`.

Tests that pin the rules to real events: the CloudFront-only bucket policy and the EventBridge-only SQS policy from Day 0 must **not** count as public; the probe cleanup must count as destructive; every MCP-made API call must appear exactly once, under its tool call. Lambda's versioned event names (`AddPermission20150331v2`) are normalized. `iam:PassRole` is left out of the rules because CloudTrail never records it.

## The review answers

Per session, `/api/review` and `/api/least-privilege` answer the third question. Each is built on an AWS service rather than a replacement for one ([D-026](../journey/decisions.md), [D-027](../journey/decisions.md)).

### What the session left running

- Each API call records the resources it created or deleted (about 30 resource types; IDs from the response, which is available only at ingest).
- Per session: **cleaned up** (created and deleted in the session), **left running** (still exists, checked through the **Cloud Control API** `GetResource`), **removed later**, and **removed pre-existing** (deleted something the session didn't create).
- Create-or-update calls (`PutRule`, `PutMetricAlarm`) count as updates when the resource was recorded earlier.
- Idle cost per month at us-east-1 list price; the 12 prices used were checked against the **AWS Price List API**.
- Day 0's build session left a bucket, a distribution, an OAC and a certificate running: $0/month idle. The EventBridge probe session cleaned up its queue and rule.

### Guardrails from what the agent did

- Each risky class the session showed becomes an IAM deny statement, in two layers:
  - the agent's identity, which covers MCP, Terraform and CLI alike (an MCP-only guardrail would have missed the 558 Terraform calls);
  - the MCP channel, with the AWS MCP Server's condition key `aws:ViaAWSMCPService`.
- Destructive and identity-escalation denies exempt resources the agent created in the same session. Example: "Delete only what the agent created" exempts exactly the queue and rule the probe session created and then cleaned up.
- Every proposal is validated with **IAM Access Analyzer `ValidatePolicy`**, both as an identity policy and as an SCP: 0 findings for every generated policy.

### Least privilege

- **Instant preview** from the recorded calls, with CloudTrail event names mapped to IAM actions (`ListBuckets` → `s3:ListAllMyBuckets`, `GetBucketCors` → `s3:GetBucketCORS`, …). Access-denied calls are dropped; not-found errors are kept, because the call was allowed (Terraform probes optional bucket settings on every plan). Calls AWS services made under the agent's identity (`invokedBy: lambda.amazonaws.com`) are listed separately.
- **IAM Access Analyzer policy generation** for the same principal and window. It works on Identity Center roles. On Day 1's build session it took 3 min 27 s and returned 75 actions with resource placeholders.
- **The comparison is shown, not hidden.** After fixes, 72 of 75 actions matched. Access Analyzer missed `logs:FilterLogEvents` (18 successful calls) and `s3:ListTagsForResource` (18 calls), and added three actions with no CloudTrail event. Both miss `iam:PassRole`, which CloudTrail doesn't record; Chaperone recovers it from the request parameters of `CreateFunction` and scopes it to the roles actually passed.

## Interfaces

| Interface | What it is |
|---|---|
| HTTP API | `chaperone-api` Lambda, function URL with IAM auth: `/api/sessions`, `/api/session`, `/api/what-happened`, `/api/risky`, `/api/review`, `/api/least-privilege`. `id=me` resolves to the caller's latest session from the function URL's IAM auth. |
| MCP server | [`mcp/server.py`](../mcp/server.py): a local stdio server with five tools (`list_sessions`, `what_did_the_agent_do`, `risky_calls`, `review_session`, `least_privilege`), a thin client over the HTTP API signed with SigV4 ([D-028](../journey/decisions.md)). It needs one permission, `lambda:InvokeFunctionUrl`, and calls no model: it runs inside your own agent, with your own model. Function URL calls are data events, so reviewing a session doesn't add to it. Answers are 2–15 KB and take 3.5–8 s. |
| Console | A static site on S3 + CloudFront (Origin Access Control) at the custom domain. The session replay is being built. |

The live site needs no model call per visitor: a plain-English summary of each published session is generated once with Bedrock and stored, and "Ask Chaperone" offers suggested questions whose answers are computed ahead of time through the same query functions ([D-029](../journey/decisions.md)).

## The AWS services it builds on

Chaperone is the review step on top of AWS's own pieces, and its output feeds AWS controls ([D-023](../journey/decisions.md)).

| AWS service | Role in Chaperone |
|---|---|
| IAM Identity Center | The agent's own identity with short sessions; the basis of attribution |
| AWS MCP Server | Produces the tool-call events with `downstreamRequests`; its condition key `aws:ViaAWSMCPService` scopes the guardrails |
| CloudTrail | Source of truth: the multi-region trail, `LookupEvents` for tool calls, sign-ins and reconcile |
| EventBridge | Near-real-time delivery of API calls, forwarded from every enabled region |
| Lambda, DynamoDB | Ingest, poller, query API; the event store |
| Cloud Control API | Checks whether what a session created still exists |
| AWS Price List API | Idle cost of what was left running |
| IAM Access Analyzer | `ValidatePolicy` on every guardrail and preview; policy generation for least privilege |
| S3, CloudFront, ACM | The console |
| Bedrock | Session summaries generated once at publish time (planned) |

Where it sits next to other AWS services: Bedrock AgentCore governs agents you build and host, and coding agents calling AWS through the AWS MCP Server or the CLI don't pass through it. Amazon Detective profiles role sessions for security investigations, but it doesn't know about MCP tool calls, doesn't separate agent from human, and doesn't produce a least-privilege policy. CloudWatch Coding Agent Insights reports agents' usage and spend, not what they did to the account.

## Cost

Built on free or near-free tiers, with caps where a bill could run away.

| Component | Cost |
|---|---|
| CloudTrail trail | First copy of management events is free |
| EventBridge | Free for AWS service events on the default bus; cross-region forwarding about $1 per million events |
| Lambda (3 functions, arm64) | Within the always-free tier |
| DynamoDB | On-demand, about $0.63 per million writes. Day 1's ~20,000 writes, backfill included, cost about a cent. Capped at 100 units/s. |
| `LookupEvents`, Access Analyzer policy generation and `ValidatePolicy` | No charge |
| S3 + CloudFront | Cents; CloudFront within its always-free tier |
| Account guard | AWS Budgets alert at $10/month |

No part of the live site calls a model per visitor, so judges' and visitors' clicks don't add model cost.

## Known gaps

- KMS crypto calls (`Decrypt`, `GenerateDataKey`) made by AWS services on their own don't reach EventBridge here; the reconcile covers the agent's own KMS calls.
- AWS hides MCP tool arguments, so Chaperone shows what the agent called, not the script it wrote.
- Documentation tools of the AWS MCP Server (`search_documentation`, `read_documentation`) leave no CloudTrail events.
