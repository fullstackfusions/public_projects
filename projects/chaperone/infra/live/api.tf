# Query API (D-026): the review answers as JSON, for the web console and the MCP server.
# Function URL with IAM auth; CloudFront (OAC) will sit in front of it with the console.

# Read permissions for "left running" existence checks: the union of the Cloud Control read
# handlers' permissions for the resource types in backend/chaperone/resources.py, taken from
# their CloudFormation registry schemas (DescribeType, 2026-09-25), minus four that an
# existence check must not hold: secretsmanager:GetSecretValue (reads the secret),
# lambda:GetFunction (returns environment variables), kms:Decrypt, iam:PassRole. Those types
# use a narrower native call instead (aws_checks._native_check). Access Analyzer's
# ValidatePolicy also rejected vpc-lattice:DescribeServiceNetworkVpcEndpointAssociation,
# listed in the VPC endpoint schema but not a real IAM action.
locals {
  existence_read_actions = [
    "acm:DescribeCertificate", "acm:ListTagsForCertificate",
    "cloudfront:GetDistribution", "cloudfront:GetDistributionConfig", "cloudfront:GetOriginAccessControl",
    "cloudfront:ListTagsForResource",
    "cloudwatch:DescribeAlarms", "cloudwatch:ListTagsForResource",
    "dynamodb:DescribeContinuousBackups", "dynamodb:DescribeContributorInsights",
    "dynamodb:DescribeKinesisStreamingDestination", "dynamodb:DescribeTable", "dynamodb:DescribeTimeToLive",
    "dynamodb:GetResourcePolicy", "dynamodb:ListTagsOfResource",
    "ec2:DescribeAccountAttributes", "ec2:DescribeAddresses", "ec2:DescribeAvailabilityZones",
    "ec2:DescribeInstanceAttribute", "ec2:DescribeInstanceCreditSpecifications", "ec2:DescribeInstances",
    "ec2:DescribeInternetGateways", "ec2:DescribeLaunchTemplates", "ec2:DescribeNatGateways",
    "ec2:DescribeNetworkAcls", "ec2:DescribeNetworkInterfaces", "ec2:DescribeSecurityGroups", "ec2:DescribeSubnets",
    "ec2:DescribeTags", "ec2:DescribeVolumeAttribute", "ec2:DescribeVolumes", "ec2:DescribeVpcAttribute",
    "ec2:DescribeVpcEncryptionControls", "ec2:DescribeVpcEndpoints", "ec2:DescribeVpcs",
    "ecr:DescribeRepositories", "ecr:GetLifecyclePolicy", "ecr:GetRepositoryPolicy", "ecr:ListTagsForResource",
    "eks:DescribeCluster",
    "elasticloadbalancing:DescribeCapacityReservation", "elasticloadbalancing:DescribeLoadBalancerAttributes",
    "elasticloadbalancing:DescribeLoadBalancers", "elasticloadbalancing:DescribeTags",
    "events:DescribeRule",
    "iam:GetLoginProfile", "iam:GetPolicy", "iam:GetPolicyVersion", "iam:GetRole", "iam:GetRolePolicy",
    "iam:GetUser", "iam:GetUserPolicy", "iam:ListAttachedRolePolicies", "iam:ListAttachedUserPolicies",
    "iam:ListEntitiesForPolicy", "iam:ListGroupsForUser", "iam:ListRolePolicies", "iam:ListUserPolicies",
    "kms:DescribeKey", "kms:GetKeyPolicy", "kms:GetKeyRotationStatus", "kms:ListResourceTags",
    "lambda:ListTags",
    "logs:DescribeIndexPolicies", "logs:DescribeLogGroups", "logs:DescribeResourcePolicies",
    "logs:GetDataProtectionPolicy", "logs:ListTagsForResource",
    "rds:DescribeDBInstances",
    "route53:GetHostedZone", "route53:ListQueryLoggingConfigs", "route53:ListTagsForResource",
    "s3:GetAccelerateConfiguration", "s3:GetAnalyticsConfiguration", "s3:GetBucketAbac", "s3:GetBucketCORS",
    "s3:GetBucketLogging", "s3:GetBucketMetadataTableConfiguration", "s3:GetBucketNotification",
    "s3:GetBucketObjectLockConfiguration", "s3:GetBucketOwnershipControls", "s3:GetBucketPublicAccessBlock",
    "s3:GetBucketTagging", "s3:GetBucketVersioning", "s3:GetBucketWebsite", "s3:GetEncryptionConfiguration",
    "s3:GetIntelligentTieringConfiguration", "s3:GetInventoryConfiguration", "s3:GetLifecycleConfiguration",
    "s3:GetMetricsConfiguration", "s3:GetReplicationConfiguration", "s3:ListBucket", "s3:ListTagsForResource",
    "secretsmanager:DescribeSecret",
    "sns:GetDataProtectionPolicy", "sns:GetTopicAttributes", "sns:ListSubscriptionsByTopic", "sns:ListTagsForResource",
    "sqs:GetQueueAttributes", "sqs:ListQueueTags",
    "ssm:DescribeAssociation", "ssm:ListAssociations",
  ]
}

# --- IAM Access Analyzer service role (policy generation reads the trail's logs) ------------

data "aws_iam_policy_document" "access_analyzer_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["access-analyzer.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.me.account_id]
    }
  }
}

resource "aws_iam_role" "access_analyzer" {
  name               = "${local.name}-access-analyzer"
  assume_role_policy = data.aws_iam_policy_document.access_analyzer_assume.json
  tags               = local.project_tags
}

# Exactly the permissions the IAM user guide lists for the policy generation service role.
data "aws_iam_policy_document" "access_analyzer" {
  statement {
    actions   = ["cloudtrail:GetTrail"]
    resources = ["*"]
  }
  statement {
    actions   = ["iam:GetServiceLastAccessedDetails", "iam:GenerateServiceLastAccessedDetails"]
    resources = ["*"]
  }
  statement {
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.trail.arn, "${aws_s3_bucket.trail.arn}/*"]
  }
}

resource "aws_iam_role_policy" "access_analyzer" {
  name   = "policy-generation"
  role   = aws_iam_role.access_analyzer.id
  policy = data.aws_iam_policy_document.access_analyzer.json
}

# --- API function --------------------------------------------------------------------------

resource "aws_iam_role" "api" {
  name               = "${local.name}-api"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.project_tags
}

data "aws_iam_policy_document" "api" {
  statement {
    sid       = "ReadEvents"
    actions   = ["dynamodb:Query", "dynamodb:GetItem", "dynamodb:PutItem"]
    resources = [aws_dynamodb_table.events.arn]
  }
  statement {
    sid = "LeftRunningExistenceChecks"
    # Cloud Control API actions use the cloudformation: IAM prefix.
    actions   = concat(["cloudformation:GetResource"], local.existence_read_actions)
    resources = ["*"]
  }
  statement {
    sid = "AccessAnalyzer"
    actions = ["access-analyzer:ValidatePolicy", "access-analyzer:StartPolicyGeneration",
    "access-analyzer:GetGeneratedPolicy"]
    resources = ["*"]
  }
  statement {
    sid       = "PassOnlyTheAccessAnalyzerRole"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.access_analyzer.arn]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["access-analyzer.amazonaws.com"]
    }
  }
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.api.arn}:*"]
  }
}

resource "aws_iam_role_policy" "api" {
  name   = "api"
  role   = aws_iam_role.api.id
  policy = data.aws_iam_policy_document.api.json
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${local.name}-api"
  retention_in_days = 14
  tags              = local.project_tags
}

resource "aws_lambda_function" "api" {
  function_name    = "${local.name}-api"
  role             = aws_iam_role.api.arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "handlers.api.handler"
  filename         = data.archive_file.backend.output_path
  source_code_hash = data.archive_file.backend.output_base64sha256
  memory_size      = 512
  timeout          = 30
  # The public site can't take more than this (D-031); edge caching absorbs repeats.
  reserved_concurrent_executions = 10
  environment {
    variables = merge(local.lambda_env, {
      ACCOUNT_ID               = data.aws_caller_identity.me.account_id
      TRAIL_ARN                = aws_cloudtrail.main.arn
      ACCESS_ANALYZER_ROLE_ARN = aws_iam_role.access_analyzer.arn
    })
  }
  depends_on = [aws_cloudwatch_log_group.api, aws_iam_role_policy.api]
  tags       = local.project_tags
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "AWS_IAM"
}

output "api_url" {
  value = aws_lambda_function_url.api.function_url
}
