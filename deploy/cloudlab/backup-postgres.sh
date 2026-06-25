#!/usr/bin/env bash
set -euo pipefail

SSH_USER="${SSH_USER:-wzp}"
PRIMARY_HOST="${PRIMARY_HOST:-amd184.utah.cloudlab.us}"
REMOTE_ROOT="${REMOTE_ROOT:-/users/wzp/hify-prod}"
REMOTE_APP="$REMOTE_ROOT/app"
REMOTE_CONFIG="$REMOTE_ROOT/config"
REMOTE_BACKUP_DIR="$REMOTE_ROOT/backups/postgres"

ssh "$SSH_USER@$PRIMARY_HOST" "set -euo pipefail
mkdir -p '$REMOTE_BACKUP_DIR'
backup_file='$REMOTE_BACKUP_DIR/hify-'\"\$(date -u +%Y%m%dT%H%M%SZ)\"'.dump'
cd '$REMOTE_APP'
docker compose --env-file '$REMOTE_CONFIG/.env' -f deploy/docker-compose.yml -f '$REMOTE_CONFIG/docker-compose.prod-override.yml' exec -T postgres pg_dump -U hify -d hify -Fc > \"\$backup_file\"
find '$REMOTE_BACKUP_DIR' -name 'hify-*.dump' -type f | sort -r | tail -n +8 | xargs -r rm -f
printf '%s\n' \"\$backup_file\"
"
