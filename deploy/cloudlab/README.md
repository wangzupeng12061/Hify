# Hify CloudLab Operations

This directory codifies the current three-node CloudLab deployment for the
phase-one small rollout.

## Topology

| Host | Internal IP | Public role | Services |
|---|---:|---|---|
| `amd184.utah.cloudlab.us` | `10.10.1.1` | Cloudflare Tunnel origin | PostgreSQL, Redis, Worker, API, Web, Nginx |
| `amd182.utah.cloudlab.us` | `10.10.1.2` | private app replica | API, Web |
| `amd197.utah.cloudlab.us` | `10.10.1.3` | private app replica | API, Web |

The public entrypoint is `https://hify.888049.xyz` through Cloudflare Access and
Cloudflare Tunnel. Direct public access to API, Web, PostgreSQL, and Redis must
remain blocked.

## Remote Layout

```text
/users/wzp/hify-prod/
├── app/                         # Synced repository checkout without .git
├── config/
│   ├── .env                     # Runtime secrets and environment
│   ├── docker-compose.prod-override.yml
│   └── nginx.conf               # Primary node only
├── backups/
│   └── postgres/
└── releases/
    └── current                  # Last deployed commit marker
```

Do not deploy under `/`.

## First-Time Configuration

Create `/users/wzp/hify-prod/config/.env` on every node. Production values must
include:

```bash
HIFY_DEPLOYMENT_MODE=production
HIFY_AUTH_DEV_LOGIN_ENABLED=false
HIFY_AUTH_TRUSTED_HEADER_ENABLED=true
HIFY_AUTH_TRUSTED_EMAIL_HEADER=cf-access-authenticated-user-email
HIFY_AUTH_TRUSTED_DISPLAY_NAME_HEADER=cf-access-authenticated-user-name
HIFY_AUTH_TRUSTED_TEAM_NAME=Hify
HIFY_AUTH_TRUSTED_DEFAULT_ROLE=member
HIFY_AUTH_COOKIE_SECURE=true
```

The primary node owns PostgreSQL and Redis. All nodes use:

```bash
HIFY_DATABASE_URL=postgresql+psycopg://hify:<password>@10.10.1.1:5432/hify
HIFY_REDIS_URL=redis://10.10.1.1:6379/0
HIFY_CELERY_BROKER_URL=redis://10.10.1.1:6379/0
```

## Deploy

From the repository root:

```bash
deploy/cloudlab/deploy.sh
```

The script:

1. Syncs the repository to all nodes.
2. Installs the CloudLab compose overrides.
3. Runs Alembic migration on the primary node.
4. Rebuilds and restarts primary services.
5. Rebuilds and restarts API/Web on replica nodes.
6. Runs health and public-entrypoint checks.

## Rollback

Rollback uses the previous remote app snapshot kept by rsync backup:

```bash
deploy/cloudlab/rollback.sh
```

Rollback restores `/users/wzp/hify-prod/app` from
`/users/wzp/hify-prod/app.rollback`, restarts services, and runs health checks.
Schema rollbacks are not automated. If a migration is not backward-compatible,
restore PostgreSQL from a backup before rolling back application code.

## Backup

Run a PostgreSQL logical backup on the primary node:

```bash
deploy/cloudlab/backup-postgres.sh
```

Backups are stored under `/users/wzp/hify-prod/backups/postgres/` on `amd184`.
The script keeps the latest seven `.dump` files.

## Health Checks

```bash
deploy/cloudlab/health-check.sh
```

Expected results:

- `https://hify.888049.xyz/chat` returns `302` to Cloudflare Access for an
  unauthenticated request.
- Public direct ports `8000`, `8080`, `5432`, and `6379` on `128.110.219.95`
  are unreachable.
- All internal API replicas return `/health/ready` with `auth: ok`.

## Cloudflare Access

Current production Access settings:

- Application: `Hify`
- Domain: `hify.888049.xyz`
- Type: self-hosted
- IdP: One-time PIN
- Policy: allow `wangzupeng12061@gmail.com`
- `auto_redirect_to_identity=false`

The backend trusts `cf-access-authenticated-user-email`. This is safe only while
origin ports remain private and traffic reaches the API through Cloudflare
Access and the primary-node reverse proxy.
