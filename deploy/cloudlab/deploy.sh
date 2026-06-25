#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SSH_USER="${SSH_USER:-wzp}"
PRIMARY_HOST="${PRIMARY_HOST:-amd184.utah.cloudlab.us}"
REMOTE_ROOT="${REMOTE_ROOT:-/users/wzp/hify-prod}"
REMOTE_APP="$REMOTE_ROOT/app"
REMOTE_CONFIG="$REMOTE_ROOT/config"
REMOTE_RELEASES="$REMOTE_ROOT/releases"
REMOTE_ROLLBACK="$REMOTE_ROOT/app.rollback"

REPLICA_HOSTS=(
  "${REPLICA_AMD182_HOST:-amd182.utah.cloudlab.us}"
  "${REPLICA_AMD197_HOST:-amd197.utah.cloudlab.us}"
)
REPLICA_OVERRIDES=(
  "compose.replica-amd182.override.yml"
  "compose.replica-amd197.override.yml"
)

release_id="$(git -C "$REPOSITORY_ROOT" rev-parse --short HEAD 2>/dev/null || date -u +%Y%m%dT%H%M%SZ)"

remote() {
  local host="$1"
  shift
  ssh "$SSH_USER@$host" "$@"
}

install_remote_layout() {
  local host="$1"
  remote "$host" "mkdir -p '$REMOTE_APP' '$REMOTE_CONFIG' '$REMOTE_RELEASES' '$REMOTE_ROOT/backups/postgres'"
}

snapshot_remote_app() {
  local host="$1"
  remote "$host" "if [ -d '$REMOTE_APP' ]; then rm -rf '$REMOTE_ROLLBACK' && cp -a '$REMOTE_APP' '$REMOTE_ROLLBACK'; fi"
}

sync_repository() {
  local host="$1"
  rsync -az --delete \
    --exclude ".git" \
    --exclude ".mypy_cache" \
    --exclude ".pytest_cache" \
    --exclude ".ruff_cache" \
    --exclude "backend/.venv" \
    --exclude "apps/web/.next" \
    --exclude "apps/web/node_modules" \
    --exclude "node_modules" \
    "$REPOSITORY_ROOT/" "$SSH_USER@$host:$REMOTE_APP/"
}

install_override() {
  local host="$1"
  local override_file="$2"
  scp "$SCRIPT_DIR/$override_file" "$SSH_USER@$host:$REMOTE_CONFIG/docker-compose.prod-override.yml"
}

write_release_marker() {
  local host="$1"
  remote "$host" "printf '%s\n' '$release_id' > '$REMOTE_RELEASES/current'"
}

deploy_primary() {
  install_remote_layout "$PRIMARY_HOST"
  snapshot_remote_app "$PRIMARY_HOST"
  sync_repository "$PRIMARY_HOST"
  install_override "$PRIMARY_HOST" "compose.primary.override.yml"
  scp "$SCRIPT_DIR/nginx.conf" "$SSH_USER@$PRIMARY_HOST:$REMOTE_CONFIG/nginx.conf"
  remote "$PRIMARY_HOST" "cd '$REMOTE_APP' && docker compose --env-file '$REMOTE_CONFIG/.env' -f deploy/docker-compose.yml -f '$REMOTE_CONFIG/docker-compose.prod-override.yml' up -d --build postgres redis migration api worker web reverse-proxy"
  write_release_marker "$PRIMARY_HOST"
}

deploy_replica() {
  local host="$1"
  local override_file="$2"

  install_remote_layout "$host"
  snapshot_remote_app "$host"
  sync_repository "$host"
  install_override "$host" "$override_file"
  remote "$host" "cd '$REMOTE_APP' && docker compose --env-file '$REMOTE_CONFIG/.env' -f deploy/docker-compose.yml -f '$REMOTE_CONFIG/docker-compose.prod-override.yml' up -d --build --no-deps api web"
  write_release_marker "$host"
}

deploy_primary

for index in "${!REPLICA_HOSTS[@]}"; do
  deploy_replica "${REPLICA_HOSTS[$index]}" "${REPLICA_OVERRIDES[$index]}"
done

"$SCRIPT_DIR/health-check.sh"
