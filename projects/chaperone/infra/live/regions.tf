# CloudTrail delivers each API call to EventBridge only in the region where it happened.
# The ingest rule lives in us-east-1, so every other enabled region forwards matching
# events to the us-east-1 default bus. Found on Day 1: an UpdateTrail on the trail's home
# region (us-east-2) never reached Chaperone.
#
# Uses AWS provider v6's per-resource `region` argument, so one for_each covers all regions.

data "aws_regions" "enabled" {} # opted-in regions only

data "aws_cloudwatch_event_bus" "default" {
  name = "default"
}

locals {
  forward_regions = setsubtract(data.aws_regions.enabled.names, ["us-east-1"])
}

data "aws_iam_policy_document" "forwarder_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.me.account_id]
    }
  }
}

resource "aws_iam_role" "forwarder" {
  name               = "${local.name}-forwarder"
  assume_role_policy = data.aws_iam_policy_document.forwarder_assume.json
  tags               = local.project_tags
}

data "aws_iam_policy_document" "forwarder" {
  statement {
    actions   = ["events:PutEvents"]
    resources = [data.aws_cloudwatch_event_bus.default.arn]
  }
}

resource "aws_iam_role_policy" "forwarder" {
  name   = "forward-to-us-east-1"
  role   = aws_iam_role.forwarder.id
  policy = data.aws_iam_policy_document.forwarder.json
}

resource "aws_cloudwatch_event_rule" "forward" {
  for_each      = local.forward_regions
  region        = each.key
  name          = "${local.name}-forward-api-calls"
  description   = "Forward CloudTrail API calls to Chaperone in us-east-1"
  state         = "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS"
  event_pattern = local.api_call_pattern
  tags          = local.project_tags
}

resource "aws_cloudwatch_event_target" "forward" {
  for_each = local.forward_regions
  region   = each.key
  rule     = aws_cloudwatch_event_rule.forward[each.key].name
  arn      = data.aws_cloudwatch_event_bus.default.arn
  role_arn = aws_iam_role.forwarder.arn
}
