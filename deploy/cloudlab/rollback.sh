#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SSH_USER="${SSH_USER:-wzp}"
PRIMARY_HOST="${PRIMARY_HOST:-amd184.utah.cloudlab.us}"
REMOTE_ROOT="${REMOTE_ROOT:-/users/wzp/hify-prod}"
REMOTE_APP="$REMOTE_ROOT/app"
REMOTE_CONFIG="$REMOTE_ROOT/config"
REMOTE_ROLLBACK="$REMOTE_ROOT/app.rollback"

REPLICA_HOSTS=(
  "${REPLICA_AMD182_HOST:-amd182.utah.cloudlab.us}"
  "${REPLICA_AMD197_HOST:-amd197.utah.cloudlab.us}"
)

remote() {
  local host="$1"
  shift
  ssh "$SSH_USER@$host" "$@"
}

restore_app_snapshot() {
  local host="$1"
  remote "$host" "test -d '$REMOTE_ROLLBACK' && rm -rf '$REMOTE_APP' && cp -a '$REMOTE_ROLLBACK' '$REMOTE_APP'"
}

restart_primary() {
  restore_app_snapshot "$PRIMARY_HOST"
  remote "$PRIMARY_HOST" "cd '$REMOTE_APP' && docker compose --env-file '$REMOTE_CONFIG/.env' -f deploy/docker-compose.yml -f '$REMOTE_CONFIG/docker-compose.prod-override.yml' up -d postgres redis migration api worker web reverse-proxy"
}

restart_replica() {
  local host="$1"
  restore_app_snapshot "$host"
  remote "$host" "cd '$REMOTE_APP' && docker compose --env-file '$REMOTE_CONFIG/.env' -f deploy/docker-compose.yml -f '$REMOTE_CONFIG/docker-compose.prod-override.yml' up -d --no-deps api web"
}

restart_primary

for host in "${REPLICA_HOSTS[@]}"; do
  restart_replica "$host"
done

"$SCRIPT_DIR/health-check.sh"
