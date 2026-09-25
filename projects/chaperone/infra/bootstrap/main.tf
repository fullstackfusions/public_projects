# One-time bootstrap: the S3 bucket that holds Terraform state for infra/live.
# Applied once with local state, then its own state is migrated into the bucket.

terraform {
  required_version = ">= 1.10"
  backend "s3" {
    key = "bootstrap/terraform.tfstate"
  }
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}

provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = { project = "chaperone", managed-by = "terraform" }
  }
}

data "aws_caller_identity" "me" {}

resource "aws_s3_bucket" "state" {
  bucket = "chaperone-tfstate-${data.aws_caller_identity.me.account_id}-use1"
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Old state versions are kept 30 days so a bad apply can be rolled back.
resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    id     = "expire-old-state-versions"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration { noncurrent_days = 30 }
  }
}

output "state_bucket" {
  value = aws_s3_bucket.state.bucket
}
