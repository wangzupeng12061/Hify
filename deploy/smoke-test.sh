#!/usr/bin/env sh
set -eu

BASE_URL="${1:-${HIFY_BASE_URL:-http://localhost:8080}}"

request() {
  path="$1"
  expected="$2"
  status="$(curl -sS -o /tmp/hify-smoke-response.txt -w "%{http_code}" "$BASE_URL$path")"
  if [ "$status" != "$expected" ]; then
    echo "Smoke check failed: GET $path expected $expected got $status"
    cat /tmp/hify-smoke-response.txt
    exit 1
  fi
  echo "ok GET $path -> $status"
}

request "/" "200"
request "/api/health/live" "200"
request "/api/health/ready" "200"

echo "Hify smoke checks passed for $BASE_URL"
