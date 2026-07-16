#!/usr/bin/env bash
# upload-data.sh — sync the generated data + curated content to an S3-compatible bucket (Cloudflare R2)
# for a remote-data deploy. See DEPLOY.md for the full walkthrough.
#
# The web app reads its per-product JSON from the local filesystem by default. Set DATA_BASE_URL on the
# host (Vercel) to this bucket's PUBLIC url and the same app fetches the data over HTTP instead — which is
# how it runs on serverless (the ~894MB of data can't ship inside a function bundle).
#
# Requires the AWS CLI configured for your R2 credentials:
#   aws configure   # Access Key / Secret from an R2 API token; region: auto
# and these env vars:
#   R2_BUCKET     your bucket name              (e.g. tradepulse-data)
#   R2_ENDPOINT   your R2 S3 endpoint           (https://<accountid>.r2.cloudflarestorage.com)
set -euo pipefail

: "${R2_BUCKET:?set R2_BUCKET=your-bucket-name}"
: "${R2_ENDPOINT:?set R2_ENDPOINT=https://<accountid>.r2.cloudflarestorage.com}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AWS=(aws s3 --endpoint-url "$R2_ENDPOINT")

echo "→ data:    web/public/data  ->  s3://$R2_BUCKET/"
"${AWS[@]}" sync "$ROOT/web/public/data" "s3://$R2_BUCKET/" \
  --exclude "content/*" --content-type application/json --size-only --no-progress

echo "→ content: content          ->  s3://$R2_BUCKET/content/"
"${AWS[@]}" sync "$ROOT/content" "s3://$R2_BUCKET/content/" \
  --content-type application/json --size-only --no-progress

echo "✓ done. Set DATA_BASE_URL to the bucket's public URL (r2.dev or your custom domain) in Vercel."
