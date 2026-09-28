---
title: "Chaperone Journey — Gotchas and Surprises"
---

# Gotchas and surprises

Newest at the bottom.

1. **An administrator can't see the bill.** AdministratorAccess isn't enough for Billing, Cost Explorer or Free Tier pages; the root user must activate "IAM user and role access to Billing information" once.
2. **The 12-month Free Tier quietly expires.** An account from 2024 only has always-free offers. Plan around Lambda, DynamoDB (provisioned), CloudFront, SNS always-free; API Gateway and S3 are paid (cents).
3. **CloudTrail quick-create skips settings.** It made the trail without asking about log file validation or KMS/RDS Data event exclusions; both had to be fixed afterwards.
4. **Console defaults that cost money:** CloudTrail's full wizard defaults to SSE-KMS with a new key, and Identity Center defaults to a multi-region instance with a customer managed key. Each key is ~$1/month.
5. **Event history is per region.** Agent calls in us-east-1 don't show when the console is on us-east-2; Identity Center events show in its own region (us-east-2).
6. **`CreateToken` has no user name.** The device-code sign-in happens before any AWS identity exists, so CloudTrail shows `-`.
7. **One sign-in, twenty `AssumeRoleWithSAML`.** Identity Center issues role credentials every time a client fetches them, and the bursts line up with MCP tool calls, so the proxy appears to fetch fresh credentials per call. Collapse them into one session marker.
8. **Every AWS MCP tool call is `readOnly: false`,** even `GetCallerIdentity`. Classify by the downstream API calls, not the tool call.
9. **AWS hides the agent's script.** `CallReadWriteTool` stores arguments and results as `[HIDDEN_DUE_TO_SECURITY_REASONS]`. Good for privacy; Chaperone can't show what the agent wrote, only what it called.
10. **MCP reveals calls the trail doesn't log.** `s3:PutObject` is a data event (not recorded by a management-events trail), but it appears in the MCP event's `downstreamRequests`.
11. **`aws login` would have blurred the line.** The quickest CLI sign-in uses the human's console identity; the agent needs its own (Identity Center) or Chaperone can't separate them.
12. **The local AWS CLI is still needed with the MCP server:** the SigV4 proxy signs with the credentials `aws sso login` caches, so the CLI renews the agent's session.
13. **CloudTrail Lake is closing to new customers.** The console banner says it's closed to new customers from May 31, 2026 (AWS points to CloudWatch instead). Chaperone doesn't depend on it: EventBridge + `LookupEvents` + the trail's S3 objects are enough.
14. **An expired agent session takes the MCP server down with it.** After the 4-hour Identity Center session lapses, Claude Code's `aws-mcp` server fails at start-up (`-32602 Invalid request parameters`), which looks like a config bug. Run `aws sso login` first, then reconnect with `/mcp`. The device code itself expires after about 10 minutes if nobody approves it (`InvalidGrantException: Invalid device code provided`).
15. **`terraform plan -generate-config-out` writes config that fails its own validation.** For the CloudTrail advanced event selectors it emits `equals = []`, `ends_with = []` and so on, which the provider rejects ("requires 1 item minimum"). The file is still written; delete the empty lists (and the `null`s and `tags_all`) and plan again.
16. **CloudTrail logs the full session token** in `AssumeRoleWithSAML` responses, and the Identity Center SAML issuer URL carries the account ID base64-encoded (`Njk2…`), so a plain text search for the account ID misses it. Redact both before any recorded event goes into a repo or a video.
17. **`agent` is a DynamoDB reserved word.** `UpdateExpression: SET agent = :a` fails with a ValidationException; use `#agent` with `ExpressionAttributeNames`. It only showed up on the first agent event, because sign-in events skip that clause.
18. **Terraform's refresh looks like a wall of errors.** One plan of an S3 bucket produced ~70 `NoSuch*Configuration` / `*NotFoundError` responses as the provider probes optional settings. Chaperone separates `denied` (worth a look) from `not_found` (noise).
19. **Blind applies get blocked.** Claude Code's auto mode refused `terraform apply -auto-approve`; the working pattern is `plan -out=x.tfplan`, read the plan, `apply x.tfplan`. Good hygiene for an agent anyway, and a fitting beat for a product about watching agents.
20. **EventBridge can silently skip CloudTrail events.** 12 `kms:Decrypt` calls Lambda made for the agent were in event history but never reached the rule (cause unconfirmed; the trail excludes KMS events). Don't treat EventBridge as complete: reconcile with `LookupEvents`.
21. **Widening an EventBridge pattern can build a feedback loop.** Forwarding AWS-service events includes EventBridge's own `AssumeRole` of the forwarder role, which forwarding repeats. Exclude your own roles in the pattern (`anything-but` + `wildcard`) and test it with `TestEventPattern` first.
22. **One write per event doesn't scale to a backfill.** Put + two conditional updates per event made a 1,500-event backfill take 88 s against a 90 s timeout. Batch writes (25 per request) and one actor update per run fixed it.
23. **Documentation tools never reach CloudTrail.** The AWS MCP Server's `search_documentation` and `read_documentation` leave no events; only tools that call AWS APIs are logged.
24. **Cloud Control's IAM prefix is `cloudformation:`,** not `cloudcontrol:`. A policy with `cloudcontrol:GetResource` applies without complaint and then denies every call. Access Analyzer `ValidatePolicy` flags it (INVALID_SERVICE_IN_ACTION).
25. **Cloud Control read handlers can over-reach.** Per the CloudFormation schemas, reading an `AWS::SecretsManager::Secret` needs `secretsmanager:GetSecretValue`, an `AWS::Lambda::Function` needs `lambda:GetFunction` (returns environment variables) and `kms:Decrypt`, and an `AWS::Events::Rule` needs `iam:PassRole`. Don't grant those for an existence check.
26. **`PutRule` creates or updates.** A tool that treats every `PutRule` as a new resource reports rule updates as leftovers; check whether the resource was seen before.
27. **Not found still means allowed.** Terraform reads optional bucket settings (CORS, website, replication, object lock) and gets `NoSuchCORSConfiguration`-style errors on every plan. A least-privilege list that drops failed calls loses permissions Terraform needs; drop only access-denied.
28. **AWS services act under your identity.** Lambda encrypting environment variables logs `kms:Decrypt`/`Encrypt` with the caller's role and `invokedBy: lambda.amazonaws.com`. Don't grant the agent permissions it never used directly; IAM Access Analyzer leaves these out too.
29. **Neither CloudTrail nor Access Analyzer sees `iam:PassRole`.** Generated policies fail on the first `CreateFunction`. The role is in the request (`role`, `RoleArn`), so read it from there and scope PassRole to those ARNs. Also, Access Analyzer omitted 18 successful `logs:FilterLogEvents` calls from its generated policy: diff it against the recorded calls before using it.
30. **MCP Python SDK 2.x renamed FastMCP.** `from mcp.server.fastmcp import FastMCP` fails; it's `from mcp.server.mcpserver import MCPServer`. Result fields are snake_case (`server_info`, `is_error`). A tool's exception reaches the model only as "Error executing tool <name>" unless it's a `ToolError`, so wrap API failures (404, expired SSO) in `ToolError` or the agent can't tell what went wrong.
