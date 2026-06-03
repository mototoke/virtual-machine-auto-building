#!/usr/bin/env bash
# RustFS 初期バケット作成（初回起動後に一度実行）
set -euo pipefail

ENDPOINT="${RUSTFS_ENDPOINT:-http://localhost:9000}"
BUCKET="${RUSTFS_BUCKET_PROJECTS:-vm-projects}"
export AWS_ACCESS_KEY_ID="${RUSTFS_ACCESS_KEY:-rustfsadmin}"
export AWS_SECRET_ACCESS_KEY="${RUSTFS_SECRET_KEY:-rustfsadmin}"
export AWS_DEFAULT_REGION=us-east-1

aws --endpoint-url "$ENDPOINT" s3 mb "s3://${BUCKET}" 2>/dev/null || true
aws --endpoint-url "$ENDPOINT" s3api put-bucket-versioning \
  --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled 2>/dev/null || true

echo "Bucket ready: s3://${BUCKET} @ ${ENDPOINT}"
