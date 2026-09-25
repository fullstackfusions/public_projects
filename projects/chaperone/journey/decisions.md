---
title: "Chaperone Journey — Decision Log"
---

# Decision log

Append-only. Each entry: context, options, choice, why. A reversed decision gets a new entry pointing at the old one.

## D-001 · Join the hackathon (2026-09-24)
- **Context:** 8 days left. Prize is AWS credits (no cash value).
- **Choice:** join, with a hard checkpoint: live on a public URL by Sun Sep 27, or drop.
- **Why:** a public, AWS-hosted artifact is worth it even without winning; serverless keeps cost near zero.

## D-002 · Idea: Chaperone (2026-09-24)
- **Choice:** Chaperone (agent flight recorder).
- **Why:** Chaperone fits the hackathon's theme exactly, makes the ship-gate proof part of the product, and its data is the build itself: real, with no simulator.

## D-003
(internal, not published)

## D-004
(internal, not published)

## D-005
(internal, not published)

## D-006 · Build region us-east-1; trail stays in us-east-2 (2026-09-24)
- **Choice:** leave `chaperone-trail` in Ohio (multi-region, so it records everything); build the app in us-east-1.
- **Why:** CloudFront certificates must be in us-east-1, and global-service events (IAM, STS, CloudFront) reach EventBridge there.

## D-007 · Agent identity via IAM Identity Center, not access keys (2026-09-24)
- **Options:** IAM Identity Center user + permission set with short sessions; or an IAM role/user with a long-lived access key on the VPS.
- **Choice:** Identity Center user `chaperone-agent`, permission set `ChaperoneAgent` (AdministratorAccess, 4-hour sessions), device-code sign-in on hermes.
- **Why:** the agent never shares the human's identity (so Chaperone can tell them apart) and never holds a permanent key. Full admin is deliberate: the story is "it had admin and needed only N actions".

## D-008 · Identity Center single-region instance (2026-09-24)
- **Choice:** single-region over the default multi-region instance.
- **Why:** multi-region uses a customer managed KMS key (~$1/month) and adds nothing for one person.

## D-009 · Connect via the managed AWS MCP Server with SigV4 proxy (2026-09-25)
- **Options:** OAuth (browser sign-in) vs SigV4 through `mcp-proxy-for-aws`.
- **Choice:** SigV4 proxy with `AWS_PROFILE=chaperone-agent`.
- **Why:** hermes is headless; SigV4 is AWS's recommendation for terminal agents. Not `aws login`, which would use the human's console identity.

## D-010
(internal, not published)

## D-011
(internal, not published)

## D-012 · Live demo on `chaperone.fullstackfusions.com` (2026-09-25)
- **Choice:** custom subdomain over the raw `cloudfront.net` URL. DNS on Cloudflare (DNS only, not proxied), certificate from ACM in us-east-1.

## D-013 · Terraform for infrastructure (2026-09-25)
- **Options:** Terraform (Mihir's existing tool) vs AWS CDK.
- **Choice:** Terraform.
- **Why:** already in Mihir's stack, so no learning cost in an 8-day sprint; plain HCL plans are easy to show on screen. Day 0's hand-made resources (bucket, OAC, distribution, certificate) get imported or recreated so everything live is in code.

## D-014 · Palette "Black Box" and the design rules (2026-09-25)
- **Context:** Mihir wants the UI to look classy and follow a set of frontend rules (own analogous palette, tints/tones/shades, measured contrast, signature visual, state never by colour alone).
- **Choice:** slate-steel palette "Black Box" (Frost, Steel, Slate, Gunmetal, Black Box), risk colours outside the palette each paired with a Lucide icon and label; signature visual "the flight path" (session replay).
- **Why:** slate-steel was an unused hue family and fits a flight recorder; the colours Mihir shared as references were ~84% `#101820`, right next to Black Box `#0E151D`. Contrast was computed, not assumed: Slate fails as text (4.47:1) so it's for lines only; `surface-3` fails behind status text so it's for borders and hover only. Script: [`design/palette.py`](../design/palette.py).

## D-015 · Design in React for the sprint, Figma afterwards (2026-09-25)
- **Options:** Figma first (Mihir designs frames, ~1 day) vs design directly in React with the measured tokens and review live.
- **Choice:** React directly for this sprint; Figma frames afterwards.
- **Why:** no spare day in the schedule, and judges score the live app, not the design file. The tokens, contrast rules and screen list in the draft stand in for the Figma tokens page.

## D-016
(internal, not published)

## D-017 · Three questions, answered where you already work (2026-09-25)
- **Context:** Mihir wants a gentle learning curve and wants Chaperone inside the tools engineers already use (Amazon Q, Claude Code and other MCP-capable IDEs), plus its own chat, so users lean on AI instead of clicking through another website.
- **Users:** engineers running coding agents against AWS (primary users); platform, cloud and security leads (buyers); auditors later.
- **Choice:** one query layer answering three questions (what did the agent do, was anything risky, what access does it need), exposed as an MCP server, a Bedrock chat on the website, and the replay screen. The website stays the judges' way in; no public hosted MCP endpoint during the sprint.
- **Why:** one MCP server reaches every MCP-capable agent at once; sharing one query layer keeps the build small; judges can still try the AI on the live URL. Build priority: pipeline + rules → query layer → MCP server → website → receipt hook (stretch).

## D-018 · Hybrid ingest: EventBridge for API calls, polling for MCP tool calls (2026-09-25)
- **Evidence:** a probe rule matching every event from `:chaperone-agent` (with all management events, read-only included) received 6 `AwsApiCall` events within 4 minutes but no `AwsMcpEvent`, while `LookupEvents` showed both `CallReadWriteTool` events.
- **Choice:** EventBridge rule → Lambda for API-call events (near-real-time; `invokedBy: aws-mcp.amazonaws.com` already marks MCP-made calls). A scheduled Lambda (every minute) calls `LookupEvents` with `EventSource = aws-mcp.amazonaws.com` to fetch tool-call events and their `downstreamRequests`. The two are joined on request ID in either order.
- **Why:** the grouping under tool calls is the product's core, and EventBridge doesn't carry it. `LookupEvents` is free and its rate limit (about 2 calls a second) is far above one call a minute. Reading the trail's S3 files is the fallback if `LookupEvents` proves too slow.

## D-019 · Adopt Day 0 into Terraform by import, state in S3 with native locking (2026-09-25)
- **Options:** recreate the Day 0 resources from Terraform (new bucket, new distribution, new DNS records) vs import them as they are; DynamoDB lock table vs S3 native locking.
- **Choice:** `import` blocks plus `-generate-config-out`, then rewrite the generated HCL into readable files with references instead of IDs; the first plan had to show 12 imports and 0 changes. State lives in a versioned, encrypted bucket `chaperone-tfstate-<account>-use1` with `use_lockfile = true` (no DynamoDB table). A tiny `infra/bootstrap` stack creates the bucket and then moves its own state into it.
- **Why:** recreating would change the CloudFront domain and break the Cloudflare CNAME and live URL two days before the checkpoint. A zero-change import proves the code matches what the agent built. S3 native locking (Terraform ≥ 1.10) is one less resource to pay for and explain.

## D-020 · Store events per actor; build sessions when reading (2026-09-25)
- **Context:** the draft keyed items by `SESSION#<id>`, so each write would need to know the actor's current session. Events arrive from two paths (EventBridge within ~10–30 s, the poller up to ~15 min later), in any order, from concurrent Lambdas.
- **Options:** a shared "current session" record updated with conditional writes vs keying events by actor and time and grouping them into sessions in the query layer.
- **Choice:** `PK = ACTOR#<actor>`, `SK = <time>#<KIND>#<eventID>`; sessions (30-minute idle gap), the tool-call/API-call join and the risk roll-up are pure functions run at read time.
- **Why:** no race conditions and no ordering assumptions; writes are idempotent, so the poller, a backfill and EventBridge can overlap safely; session rules can change without rewriting data; everything interesting is unit-testable on the recorded fixtures. Cost: one query per actor per view, which is small at this scale.

## D-021 · An agent is known by its identity, not its user agent (2026-09-25)
- **Evidence:** the first live run filed 558 Terraform calls as plain `sdk` traffic: Terraform's user agent doesn't mention Claude Code, though the agent ran it.
- **Choice:** sessions of roles whose name starts with a configured prefix (`AGENT_ROLE_PREFIXES`, default `AWSReservedSSO_ChaperoneAgent_`) are agent activity whatever tool made the call; the user agent only adds the channel (`mcp`, `terraform`, `cli`, `agent-cli`).
- **Why:** this is what D-007 bought: with its own identity, everything the agent does is attributable, including through tools that don't announce it. Without the identity, Chaperone could only guess from user-agent strings.

## D-022 · Forward API calls from every enabled region to us-east-1 (2026-09-25)
- **Evidence:** an `UpdateTrail` on the trail's home region (us-east-2) never reached Chaperone: CloudTrail delivers an event to EventBridge only in the region where it happened.
- **Choice:** in each of the 16 other enabled regions, an EventBridge rule with the same pattern (shared local) forwards to the us-east-1 default bus through a role that can only `events:PutEvents` there. One `for_each` using AWS provider v6's per-resource `region`.
- **Why:** an agent working in an unexpected region is exactly what a reviewer needs to see; cost is ~$1 per million forwarded events. Proof: a no-op `UpdateTrail` in us-east-2 and a `DescribeVpcs` in eu-west-1 at 15:50:29 were stored within ~27 s, the first as `audit_tampering`.

## D-023 · Complement AWS, never compete (2026-09-25)
- **Context:** Mihir asked whether Chaperone overlaps Bedrock AgentCore; the rule is to complement AWS services or fill a gap none of them covers.
- **Finding:** AgentCore governs agents you build and host (Policy acts on tool calls through AgentCore Gateway); coding agents acting on an account through the AWS MCP Server or CLI never pass through it. The closest AWS service is Amazon Detective (role-session profiles for security investigations), which knows nothing of MCP tool calls, agent vs human, or least privilege. Full table in [docs/architecture.md](../docs/architecture.md#the-aws-services-it-builds-on).
- **Choice:** position Chaperone as the review step on top of AWS's own pieces (Identity Center, AWS MCP Server, CloudTrail, Access Analyzer), and make its output feed AWS controls: suggested IAM/SCP statements using `aws:ViaAWSMCPService` / `aws:CalledViaAWSMCP`, and the Access Analyzer policy. Never pitch it as threat detection or investigation.

## D-024 · Who acted vs how: actor type, channel and operator; reconcile for completeness (2026-09-25)
- **Context:** Mihir asked for full observability, with every event labelled human, agent or MCP. A coverage check (CloudTrail vs stored, last 3 h) found humans 46/46, agent 85/97, MCP tool calls 2/2, and AWS services acting on their own 0/~960 (dropped by the identity filter). The 12 missing agent events were `kms:Decrypt` calls Lambda made on the agent's behalf; EventBridge never delivered them although the rule matches.
- **Choice:** MCP is a channel, not an actor. Each event carries `actor_type` (human, agent, workload, service: who the identity is), `via` (mcp, console, cli, terraform, sdk, service:x: how) and `operated_by` (who drove it; anything through MCP or an agent CLI is an agent, whatever identity it used). An agent on a human or workload identity is flagged `agent_on_human_identity` / `agent_on_workload_identity`. Capture widened to federated, web-identity (CI), cross-account and AWS-service identities; service events kept 7 days. The poller reconciles each agent's activity with `LookupEvents` across all regions, one fifth of them per run.
- **Why:** a three-way human/agent/MCP label would hide the most important case (an agent borrowing a person's identity through MCP). Reconcile turns "EventBridge usually delivers" into "every agent event is recorded", which is the product's promise.
- **Guard:** AWS services assuming a `chaperone-*` role (Lambda cold starts, the EventBridge forwarder) are excluded in the event pattern, not only in code, because forwarding them would generate more of them. Verified with `TestEventPattern` on 8 cases before applying.

## D-025 · DynamoDB on-demand with a throughput cap, not provisioned (2026-09-25)
- **Evidence:** with 10 provisioned WCU, backfilling ~1,650 events produced 2,755 write throttle events; the poller ran into its 90 s timeout twice. `LookupEvents` was not the bottleneck (1,000 events in 4 s).
- **Choice:** `PAY_PER_REQUEST` with `on_demand_throughput` capped at 100 read and 100 write units per second; poller timeout 300 s for one-off backfills (scheduled runs take seconds); backfills invoked asynchronously.
- **Why:** reverses the draft's "provisioned, always free" choice. On-demand writes cost about $0.63 per million: today's ~20k writes are about a cent, steady state cents a month, and the cap makes a runaway bill impossible. A recorder that drops events under load is worse than one that costs a cent.

## D-026 · The review answers: left running, guardrails, least privilege, built on AWS services (2026-09-25)
- **Context:** Mihir agreed to make the complement story concrete for AWS judges: two answers no AWS service gives for an agent's session, built from AWS's own parts.
- **Left running:** each API call records the resources it created or deleted (a table of ~30 types; IDs from the response, only available at ingest). Per session: cleaned up (created and deleted in the session), left running (still exists, checked through the **Cloud Control API**), removed later, and **removed pre-existing** (deleted something the session didn't create). Idle cost per month at us-east-1 list price, 12 prices checked against the **AWS Price List API**. Create-or-update calls (`PutRule`, `PutMetricAlarm`) count as updates when the resource was recorded earlier.
- **Guardrails:** each risky class the session showed becomes a deny statement, two layers: the agent's identity (covers MCP, Terraform, CLI; an MCP-only rule would have missed 558 Terraform calls) and the MCP channel (`aws:ViaAWSMCPService`, per the AWS Security Blog of 2026-03-02). Destructive and identity-escalation denies exempt resources the agent created in that session. Every proposal is checked with **IAM Access Analyzer ValidatePolicy** (identity policy and SCP).
- **Least privilege:** instant preview from recorded calls (CloudTrail names mapped to IAM actions) plus **IAM Access Analyzer policy generation** for the principal over the session window. Works on Identity Center roles (`aws-reserved/sso.amazonaws.com/...`).
- **Chaperone's own permissions:** existence-check reads taken from the CloudFormation schemas' read handlers, minus four an existence check must not hold (`secretsmanager:GetSecretValue`, `lambda:GetFunction`, `kms:Decrypt`, `iam:PassRole`; those types use a narrower native call). Its own policy went through ValidatePolicy too, which caught `cloudcontrol:GetResource` (the prefix is `cloudformation:`) and a non-existent vpc-lattice action.

## D-027 · Least privilege: show the preview and Access Analyzer side by side, with the differences (2026-09-25)
- **Evidence:** on the Day 1 build session, Access Analyzer took 3 min 27 s and returned 75 actions with resource placeholders. The corrected preview matched 72. Access Analyzer missed `logs:FilterLogEvents` and `s3:ListTagsForResource` and added three actions with no CloudTrail event. Both miss `iam:PassRole`; only Chaperone can recover it (from request parameters).
- **Choice:** the console shows the instant preview first, then Access Analyzer's policy when the job finishes, with a diff: "only AWS saw", "only Chaperone saw", "passed roles". Neither is labelled authoritative.
- **Why:** complement, never compete (D-023): Access Analyzer adds resource scoping, and Chaperone adds per-session timing, PassRole, and a check of AWS's output against the real calls.

## D-028 · MCP server: a thin client over the HTTP API, with "me" and compact answers (2026-09-25)
- **Options:** (a) import the query layer and read DynamoDB directly; (b) call the API's function URL with SigV4.
- **Choice:** (b). Local stdio server (`mcp/server.py`, uv inline dependencies), five tools over `/api/*`. `session_id="me"` resolves server-side from the IAM caller, so an agent reviews its own latest session without knowing its ID. The query layer gained `answers.py` (collapsed, capped answers sized for a model's context), shared with the console and the Bedrock chat later.
- **Why:** one code path for MCP, console and chat; the MCP server needs one permission (`lambda:InvokeFunctionUrl`) instead of table access, which is the least-privilege story Chaperone tells about agents; function URL calls are data events, so reviewing a session doesn't add management events to it. Still no public hosted MCP endpoint (D-017 scope stands).

## D-029 · Live site: AI answers computed once, MCP shown as a clip, no per-visitor LLM cost (2026-09-25)
- **Context:** Mihir asked whether the MCP server must stay up for two weeks of judging and whether he pays for judges' LLM usage. The MCP server runs in the user's own agent with the user's own model, and its tools call no model, so there is nothing to host and no LLM cost. Judges can't point it at this account (it needs credentials), and the rules require only a live public app reachable by judges and the AI scorer.
- **Choice:** (1) a plain-English explanation of each published session, generated once with Bedrock and stored; visitors read the stored text. (2) "Ask Chaperone": suggested questions per session with answers pre-computed through the same query functions, instead of a free-text box. (3) An **"MCP: seen from the agent"** panel on the site: on one side a short muted **looping video (MP4/WebM, not GIF)** of the self-review moment (`risky_calls("me")`), on the other the real answers captured from that run, account IDs masked, with a **YouTube link** to the full walkthrough. (Mihir confirmed looping video over GIF and the YouTube link, 2026-09-25.) Live free-text chat only later, and only behind a daily cap, a small model, and limited concurrency.
- **Why:** judges still see the AI and the MCP integration, while the bill stays at a few cents total through judging (to the week of Oct 12) no matter how often judges or the automated scorer click. Nothing a visitor does can call a model.
