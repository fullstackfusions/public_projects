# Ingest pipeline (D-018, D-020): two paths into one DynamoDB table.
#
#   CloudTrail -> EventBridge rule -> ingest Lambda   (API calls, near real time)
#   schedule (1 min) -> poller Lambda -> LookupEvents (MCP tool calls, sign-ins)
#
# Near-free: on-demand DynamoDB with a throughput cap, arm64 Lambdas, 14-day logs.

locals {
  name = "chaperone"
  lambda_env = {
    TABLE_NAME = aws_dynamodb_table.events.name
    # Role-name prefixes whose sessions are coding agents (the agent's own identity, D-007).
    AGENT_ROLE_PREFIXES = "AWSReservedSSO_ChaperoneAgent_"
  }
  backend_dir = "${path.module}/../../backend"
}

# --- storage ------------------------------------------------------------------------

# On-demand, not provisioned (D-025): 10 provisioned WCU throttled a 1,650-event backfill
# 2,755 times. The cap bounds the worst case; normal use costs cents a month.
resource "aws_dynamodb_table" "events" {
  name         = local.name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  on_demand_throughput {
    max_read_request_units  = 100
    max_write_request_units = 100
  }

  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "SK"
    type = "S"
  }

  # Events carry expires_at = event time + 90 days (CloudTrail's own event-history window).
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = local.project_tags
}

# --- code -----------------------------------------------------------------------------

data "archive_file" "backend" {
  type        = "zip"
  source_dir  = local.backend_dir
  output_path = "${path.module}/.build/backend.zip"
  excludes    = ["tests", "tests/**", "**/__pycache__", "**/__pycache__/**", ".pytest_cache", ".pytest_cache/**"]
}

# --- IAM ------------------------------------------------------------------------------

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Role names start with "chaperone-" on purpose: model.py skips these principals so
# Chaperone never records itself.
resource "aws_iam_role" "ingest" {
  name               = "${local.name}-ingest"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.project_tags
}

resource "aws_iam_role" "poller" {
  name               = "${local.name}-poller"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.project_tags
}

data "aws_iam_policy_document" "ingest" {
  statement {
    actions   = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:GetItem"]
    resources = [aws_dynamodb_table.events.arn]
  }
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.ingest.arn}:*"]
  }
}

data "aws_iam_policy_document" "poller" {
  statement {
    actions   = ["dynamodb:PutItem", "dynamodb:BatchWriteItem", "dynamodb:UpdateItem", "dynamodb:GetItem", "dynamodb:Query"]
    resources = [aws_dynamodb_table.events.arn]
  }
  statement {
    # LookupEvents has no resource-level permissions.
    actions   = ["cloudtrail:LookupEvents"]
    resources = ["*"]
  }
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.poller.arn}:*"]
  }
}

resource "aws_iam_role_policy" "ingest" {
  name   = "ingest"
  role   = aws_iam_role.ingest.id
  policy = data.aws_iam_policy_document.ingest.json
}

resource "aws_iam_role_policy" "poller" {
  name   = "poller"
  role   = aws_iam_role.poller.id
  policy = data.aws_iam_policy_document.poller.json
}

# --- functions -----------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "ingest" {
  name              = "/aws/lambda/${local.name}-ingest"
  retention_in_days = 14
  tags              = local.project_tags
}

resource "aws_cloudwatch_log_group" "poller" {
  name              = "/aws/lambda/${local.name}-poller"
  retention_in_days = 14
  tags              = local.project_tags
}

resource "aws_lambda_function" "ingest" {
  function_name    = "${local.name}-ingest"
  role             = aws_iam_role.ingest.arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "handlers.ingest.handler"
  filename         = data.archive_file.backend.output_path
  source_code_hash = data.archive_file.backend.output_base64sha256
  memory_size      = 256
  timeout          = 15
  environment { variables = local.lambda_env }
  depends_on = [aws_cloudwatch_log_group.ingest, aws_iam_role_policy.ingest]
  tags       = local.project_tags
}

resource "aws_lambda_function" "poller" {
  function_name    = "${local.name}-poller"
  role             = aws_iam_role.poller.arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "handlers.poller.handler"
  filename         = data.archive_file.backend.output_path
  source_code_hash = data.archive_file.backend.output_base64sha256
  memory_size      = 256
  timeout          = 300 # scheduled runs take seconds; room for one-off backfills
  # One run at a time: overlapping runs would both write the same new events.
  reserved_concurrent_executions = 1
  environment {
    variables = merge(local.lambda_env, {
      MCP_REGION             = "us-east-1"
      IDENTITY_CENTER_REGION = "us-east-2"
      # Re-read agents' activity everywhere: EventBridge can skip events (D-024).
      RECONCILE_REGIONS = join(",", sort(data.aws_regions.enabled.names))
    })
  }
  depends_on = [aws_cloudwatch_log_group.poller, aws_iam_role_policy.poller]
  tags       = local.project_tags
}

# --- triggers ------------------------------------------------------------------------

# Shared with the forwarding rules in regions.tf, so every region filters the same way:
# every identity type (D-024), minus Chaperone's own chaperone-* roles. AWS services
# assuming a chaperone-* role (Lambda starting a function, EventBridge forwarding) are
# excluded here, not just in code: forwarding them would create more of them (a loop).
locals {
  api_call_pattern = jsonencode({
    "detail-type" = ["AWS API Call via CloudTrail"]
    detail = {
      "$or" = [
        { userIdentity = { type = ["IAMUser", "Root", "FederatedUser", "WebIdentityUser", "AWSAccount", "IdentityCenterUser"] } },
        {
          userIdentity = {
            type           = ["AssumedRole"]
            sessionContext = { sessionIssuer = { userName = [{ "anything-but" = { prefix = "chaperone-" } }] } }
          }
        },
        { userIdentity = { type = ["AWSService"] }, eventName = [{ "anything-but" = ["AssumeRole"] }] },
        {
          userIdentity      = { type = ["AWSService"] }
          eventName         = ["AssumeRole"]
          requestParameters = { roleArn = [{ "anything-but" = { wildcard = "*:role/chaperone-*" } }] }
        },
      ]
    }
  })
}

# Every management event in us-east-1 (IAM and other global services land here too),
# read-only included; other regions forward theirs here (regions.tf).
resource "aws_cloudwatch_event_rule" "api_calls" {
  name          = "${local.name}-api-calls"
  description   = "CloudTrail API calls to Chaperone ingest"
  state         = "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS"
  event_pattern = local.api_call_pattern
  tags          = local.project_tags
}

resource "aws_cloudwatch_event_target" "ingest" {
  rule = aws_cloudwatch_event_rule.api_calls.name
  arn  = aws_lambda_function.ingest.arn
  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 10
  }
}

resource "aws_lambda_permission" "events_invoke_ingest" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.api_calls.arn
}

resource "aws_cloudwatch_event_rule" "poll" {
  name                = "${local.name}-poll"
  description         = "Fetch MCP tool calls and sign-ins every minute"
  schedule_expression = "rate(1 minute)"
  tags                = local.project_tags
}

resource "aws_cloudwatch_event_target" "poller" {
  rule = aws_cloudwatch_event_rule.poll.name
  arn  = aws_lambda_function.poller.arn
}

resource "aws_lambda_permission" "events_invoke_poller" {
  statement_id  = "AllowSchedule"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.poller.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.poll.arn
}

output "table_name" {
  value = aws_dynamodb_table.events.name
}
