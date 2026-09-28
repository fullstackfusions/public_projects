variable "domain" {
  description = "Custom domain for the console (CloudFront alias and ACM certificate). DNS is managed outside AWS."
  type        = string
  default     = "chaperone.fullstackfusions.com"
}

variable "trail_bucket_suffix" {
  description = "Random suffix of the CloudTrail log bucket (aws-cloudtrail-logs-<account>-<suffix>), as created by the console's quick-create."
  type        = string
  default     = "063302cf"
}
