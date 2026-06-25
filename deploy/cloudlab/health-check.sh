#!/usr/bin/env bash
set -euo pipefail

SSH_USER="${SSH_USER:-wzp}"
PRIMARY_HOST="${PRIMARY_HOST:-amd184.utah.cloudlab.us}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://hify.888049.xyz}"
PRIMARY_PUBLIC_IP="${PRIMARY_PUBLIC_IP:-128.110.219.95}"

INTERNAL_API_URLS=(
  "http://10.10.1.1:8000/health/ready"
  "http://10.10.1.2:8000/health/ready"
  "http://10.10.1.3:8000/health/ready"
)

require_cloudflare_access_redirect() {
  local headers
  headers="$(curl -sSI --max-time 10 "$PUBLIC_BASE_URL/chat")"
  printf '%s\n' "$headers" | grep -Eq '^HTTP/[0-9.]+ 30[1278]' || {
    printf '%s\n' "$headers"
    printf 'Expected Cloudflare Access redirect from %s/chat\n' "$PUBLIC_BASE_URL" >&2
    exit 1
  }
  printf '%s\n' "$headers" | grep -Eiq 'location: .*cloudflareaccess\.com' || {
    printf '%s\n' "$headers"
    printf 'Expected redirect location to Cloudflare Access\n' >&2
    exit 1
  }
  printf 'ok public entrypoint is protected by Cloudflare Access\n'
}

require_public_port_blocked() {
  local port="$1"

  if nc -z -w 3 "$PRIMARY_PUBLIC_IP" "$port" >/dev/null 2>&1; then
    printf 'Public direct TCP port must remain blocked: %s:%s\n' "$PRIMARY_PUBLIC_IP" "$port" >&2
    exit 1
  fi

  printf 'ok public direct port blocked: %s\n' "$port"
}

require_internal_health() {
  local url="$1"
  ssh "$SSH_USER@$PRIMARY_HOST" "curl -fsS --max-time 10 '$url' >/dev/null"
  printf 'ok internal health: %s\n' "$url"
}

require_primary_proxy_health() {
  ssh "$SSH_USER@$PRIMARY_HOST" "curl -fsS --max-time 10 http://127.0.0.1:80/api/health/ready >/dev/null"
  printf 'ok primary reverse proxy API health\n'
}

require_cloudflare_access_redirect

for port in 8000 8080 5432 6379; do
  require_public_port_blocked "$port"
done

for url in "${INTERNAL_API_URLS[@]}"; do
  require_internal_health "$url"
done

require_primary_proxy_health

printf 'Hify CloudLab health checks passed\n'
