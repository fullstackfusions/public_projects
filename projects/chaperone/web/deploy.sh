#!/usr/bin/env bash
# Build the console and publish it: hashed assets cached for a year, index.html never,
# then invalidate index.html so the new build shows at once.
#   AWS_PROFILE=chaperone-agent ./deploy.sh
set -euo pipefail
cd "$(dirname "$0")"
BUCKET=$(terraform -chdir=../infra/live output -raw web_bucket)
DIST=$(terraform -chdir=../infra/live output -raw distribution_id)
npm run build
aws s3 sync dist/assets "s3://$BUCKET/assets" --cache-control "public, max-age=31536000, immutable"
aws s3 sync dist "s3://$BUCKET" --exclude "assets/*" --delete --cache-control "no-cache"
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/index.html" "/" --query Invalidation.Id --output text
