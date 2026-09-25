terraform {
  required_version = ">= 1.10"
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 6.0" }
    archive = { source = "hashicorp/archive", version = "~> 2.7" }
  }
  backend "s3" {
    key = "live/terraform.tfstate"
  }
}

# Everything Chaperone runs is in us-east-1 (CloudFront certificates must be there too).
provider "aws" {
  region = "us-east-1"
}

# The account's CloudTrail trail and its log bucket live in us-east-2 (D-006).
provider "aws" {
  alias  = "use2"
  region = "us-east-2"
}

data "aws_caller_identity" "me" {}
