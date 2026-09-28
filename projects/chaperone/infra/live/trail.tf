# The account's audit trail: every region, management events (reads and writes),
# minus the two noisiest sources. Home region us-east-2 (D-006). This is Chaperone's
# source of truth; the pipeline reads it through EventBridge and LookupEvents in us-east-1.

resource "aws_s3_bucket" "trail" {
  provider = aws.use2
  bucket   = "aws-cloudtrail-logs-${data.aws_caller_identity.me.account_id}-${var.trail_bucket_suffix}"
}

resource "aws_s3_bucket_ownership_controls" "trail" {
  provider = aws.use2
  bucket   = aws_s3_bucket.trail.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "trail" {
  provider                = aws.use2
  bucket                  = aws_s3_bucket.trail.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Log files are the evidence behind every session: keep a year (the table keeps 90 days,
# and Access Analyzer reads at most 90 days back), then let them go.
resource "aws_s3_bucket_lifecycle_configuration" "trail" {
  provider = aws.use2
  bucket   = aws_s3_bucket.trail.id
  rule {
    id     = "expire-after-a-year"
    status = "Enabled"
    filter {}
    expiration {
      days = 365
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

locals {
  # Built by name, not from aws_cloudtrail.main.arn: the trail needs this policy
  # before it can be created, so a reference would be a cycle.
  trail_arn = "arn:aws:cloudtrail:us-east-2:${data.aws_caller_identity.me.account_id}:trail/chaperone-trail"
}

resource "aws_s3_bucket_policy" "trail" {
  provider = aws.use2
  bucket   = aws_s3_bucket.trail.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AWSCloudTrailAclCheck20150319-845ecafe-ea7a-4777-b568-cc4e34f6159d"
      Effect    = "Allow"
      Principal = { Service = "cloudtrail.amazonaws.com" }
      Action    = "s3:GetBucketAcl"
      Resource  = aws_s3_bucket.trail.arn
      Condition = { StringEquals = { "AWS:SourceArn" = local.trail_arn } }
      }, {
      Sid       = "AWSCloudTrailWrite20150319-d10bcda7-ce51-4bad-90dd-71c4a5aec80b"
      Effect    = "Allow"
      Principal = { Service = "cloudtrail.amazonaws.com" }
      Action    = "s3:PutObject"
      Resource  = "${aws_s3_bucket.trail.arn}/AWSLogs/${data.aws_caller_identity.me.account_id}/*"
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = local.trail_arn
          "s3:x-amz-acl"  = "bucket-owner-full-control"
        }
      }
    }]
  })
}

resource "aws_cloudtrail" "main" {
  provider                      = aws.use2
  name                          = "chaperone-trail"
  s3_bucket_name                = aws_s3_bucket.trail.id
  is_multi_region_trail         = true
  include_global_service_events = true
  enable_log_file_validation    = true # digest files: tamper evidence for the logs

  advanced_event_selector {
    name = "Management events selector"
    field_selector {
      field  = "eventCategory"
      equals = ["Management"]
    }
    field_selector {
      field      = "eventSource"
      not_equals = ["kms.amazonaws.com", "rdsdata.amazonaws.com"]
    }
  }

  depends_on = [aws_s3_bucket_policy.trail]
}
