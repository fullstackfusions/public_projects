# Public console: private S3 bucket served only through CloudFront (Origin Access Control),
# on chaperone.fullstackfusions.com. DNS is on Cloudflare: a CNAME to the distribution,
# plus the ACM validation CNAME.
#
# /api/* goes to the API function URL, also through OAC (D-031): CloudFront signs every
# request, and adds `x-chaperone-view: public` so the API masks identifiers and refuses
# `id=me` and job starts. A viewer can't drop or change that header (CloudFront overwrites it).

locals {
  domain        = var.domain
  web_origin_id = "s3-chaperone-web"
  api_origin_id = "lambda-chaperone-api"
  api_domain    = trimsuffix(trimprefix(aws_lambda_function_url.api.function_url, "https://"), "/")
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

resource "aws_cloudfront_origin_access_control" "api" {
  name                              = "chaperone-api-oac"
  description                       = "Chaperone API function URL"
  origin_access_control_origin_type = "lambda"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_response_headers_policy" "security_headers" {
  name = "Managed-SecurityHeadersPolicy"
}

# API answers: keyed on the query string only (no viewer headers, so the function URL's
# own Host reaches Lambda), cached for as long as the API's Cache-Control says.
resource "aws_cloudfront_cache_policy" "api" {
  name        = "chaperone-api"
  comment     = "Query strings only; TTL from the API's Cache-Control"
  min_ttl     = 0
  default_ttl = 0
  max_ttl     = 3600
  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "none"
    }
    query_strings_config {
      query_string_behavior = "all"
    }
  }
}

# Client-side routes (/session/..., /judges) -> the files that render them.
resource "aws_cloudfront_function" "spa_routes" {
  name    = "chaperone-spa-routes"
  runtime = "cloudfront-js-2.0"
  comment = "Serve index.html for app routes"
  publish = true
  code    = <<-JS
    function handler(event) {
      var req = event.request;
      var last = req.uri.split('/').pop();
      if (last.indexOf('.') === -1) {
        req.uri = req.uri.indexOf('/judges') === 0 ? '/judges/index.html' : '/index.html';
      }
      return req;
    }
  JS
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

  origin {
    origin_id                = local.api_origin_id
    domain_name              = local.api_domain
    origin_access_control_id = aws_cloudfront_origin_access_control.api.id
    custom_header {
      name  = "x-chaperone-view"
      value = "public"
    }
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
      origin_read_timeout    = 30
    }
  }

  default_cache_behavior {
    target_origin_id           = local.web_origin_id
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_optimized.id
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.security_headers.id
    compress                   = true
    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa_routes.arn
    }
  }

  ordered_cache_behavior {
    path_pattern               = "/api/*"
    target_origin_id           = local.api_origin_id
    viewer_protocol_policy     = "https-only"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    cache_policy_id            = aws_cloudfront_cache_policy.api.id
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.security_headers.id
    compress                   = true
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

# CloudFront may call the API only on behalf of this distribution. Function URLs need both
# actions for a service principal (the CloudFront guide shows the two add-permission calls).
resource "aws_lambda_permission" "cloudfront_url" {
  statement_id  = "AllowCloudFrontInvokeFunctionUrl"
  action        = "lambda:InvokeFunctionUrl"
  function_name = aws_lambda_function.api.function_name
  principal     = "cloudfront.amazonaws.com"
  source_arn    = aws_cloudfront_distribution.web.arn
}

resource "aws_lambda_permission" "cloudfront_invoke" {
  statement_id  = "AllowCloudFrontInvokeFunction"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "cloudfront.amazonaws.com"
  source_arn    = aws_cloudfront_distribution.web.arn
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
