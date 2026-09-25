# Public console: private S3 bucket served only through CloudFront (Origin Access Control),
# on chaperone.fullstackfusions.com. DNS is on Cloudflare: a CNAME to the distribution,
# plus the ACM validation CNAME.

locals {
  domain        = var.domain
  web_origin_id = "s3-chaperone-web"
  project_tags  = { Project = "chaperone" }
}

resource "aws_s3_bucket" "web" {
  bucket = "chaperone-web-${data.aws_caller_identity.me.account_id}-use1"
  tags   = local.project_tags
}

resource "aws_s3_bucket_ownership_controls" "web" {
  bucket = aws_s3_bucket.web.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "web" {
  bucket                  = aws_s3_bucket.web.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Only this distribution can read objects.
resource "aws_s3_bucket_policy" "web" {
  bucket = aws_s3_bucket.web.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowCloudFrontOAC"
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.web.arn}/*"
      Condition = { StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.web.arn } }
    }]
  })
}

resource "aws_acm_certificate" "web" {
  domain_name       = local.domain
  validation_method = "DNS"
  tags              = local.project_tags
}

resource "aws_cloudfront_origin_access_control" "web" {
  name                              = "chaperone-web-oac"
  description                       = "Chaperone web bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}

resource "aws_cloudfront_distribution" "web" {
  comment             = "Chaperone web (hackathon)"
  enabled             = true
  aliases             = [local.domain]
  default_root_object = "index.html"
  http_version        = "http2and3"
  is_ipv6_enabled     = true
  price_class         = "PriceClass_100"
  tags                = local.project_tags

  origin {
    origin_id                = local.web_origin_id
    domain_name              = aws_s3_bucket.web.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.web.id
  }

  default_cache_behavior {
    target_origin_id       = local.web_origin_id
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = data.aws_cloudfront_cache_policy.caching_optimized.id
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.web.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

output "web_bucket" {
  value = aws_s3_bucket.web.bucket
}

output "distribution_id" {
  value = aws_cloudfront_distribution.web.id
}

output "distribution_domain" {
  value = aws_cloudfront_distribution.web.domain_name
}
