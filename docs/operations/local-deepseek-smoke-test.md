# Local DeepSeek Smoke Test

Use this procedure after provider-runtime or release-closure changes to verify
that a published Agent can call DeepSeek, stream a Run through SSE, and write the
assistant response back to Conversations.

This is a development-only verification path. Do not use the local Fernet key,
developer login, or temporary key files in production.

## Prerequisites

- Docker is running.
- PostgreSQL and Redis ports `5432` and `6379` are available locally.
- The repository `.env` exists and contains a local-only
  `HIFY_PROVIDER_CREDENTIAL_ENCRYPTION_KEY`.
- A real DeepSeek API key is available as `DEEPSEEK_API_KEY` or stored in a
  local temporary file that is not committed.
- The web runtime uses Node `>=24 <25`. If the system Node is broken or outside
  that range, run web commands with a known-good Node path in `PATH`.

Never commit API keys, cookies, generated `.next` files, or local database
state.

## Start Local Dependencies

```bash
docker compose -f deploy/docker-compose.yml --env-file .env up -d postgres redis
```

Run migrations from the host:

```bash
cd backend
HIFY_DATABASE_URL=postgresql+psycopg://hify:hify_dev_password@127.0.0.1:5432/hify \
  uv run alembic upgrade head
```

## Start API

```bash
cd backend
export HIFY_PROVIDER_CREDENTIAL_ENCRYPTION_KEY="$(
  grep '^HIFY_PROVIDER_CREDENTIAL_ENCRYPTION_KEY=' ../.env | cut -d= -f2-
)"
HIFY_DATABASE_URL=postgresql+psycopg://hify:hify_dev_password@127.0.0.1:5432/hify \
HIFY_REDIS_URL=redis://127.0.0.1:6379/0 \
HIFY_CELERY_BROKER_URL=redis://127.0.0.1:6379/0 \
HIFY_PROVIDER_CREDENTIAL_ENCRYPTION_KEY="${HIFY_PROVIDER_CREDENTIAL_ENCRYPTION_KEY}" \
HIFY_AUTH_DEV_LOGIN_ENABLED=true \
  uv run fastapi run src/hify/bootstrap/api.py --host 127.0.0.1 --port 8000
```

Check readiness:

```bash
curl -fsS http://127.0.0.1:8000/health/ready
```

Expected result:

```json
{"status":"ok","checks":{"database":"ok","provider_credential_encryption_key":"ok","redis":"ok"}}
```

## Start Web

```bash
cd apps/web
HIFY_API_PROXY_TARGET=http://127.0.0.1:8000 \
NEXT_PUBLIC_HIFY_API_BASE_URL=/api \
  pnpm dev
```

Open `http://localhost:3000/chat`. If port `3000` is already in use by another
Next dev server for this project, reuse that server or stop it before starting a
new one.

## Functional Smoke Path

Use the UI or API to perform these checks:

1. Create a developer session with `dev@hify.local` in `Hify Dev Team`.
2. Create a `deepseek` provider using the real DeepSeek API key.
3. Add a chat model, for example `deepseek-chat`.
4. Create an Agent using that model.
5. Publish the Agent and confirm it appears in the user Chat page selector.
6. Create a Conversation, append one user message, create a Run, and execute
   `/runs/{run_id}/execute-stream`.
7. Confirm SSE emits text deltas and ends with `run.succeeded`.
8. Confirm `/conversations/{conversation_id}/messages` contains both the user
   message and an assistant message.
9. Confirm `/runs/{run_id}/diagnostics` is readable for the completed Run.

The minimum successful result is:

- API `/health/ready` returns `ok`.
- Published Agent is listed as `published`.
- Run status is `succeeded`.
- Conversation message count increases to at least 2.
- Assistant content is a model-generated response, not a fixed test prompt.

## Troubleshooting

- `Failed to fetch` in the browser usually means the Next `/api` proxy is not
  pointing to the API. Set `HIFY_API_PROXY_TARGET=http://127.0.0.1:8000` before
  starting `pnpm dev`.
- No Agent appears in the Chat page when the Agent was created in a different
  dev team. Use the same dev login team name for Provider, Agent, and Chat.
- A repeated response such as `Hify Browser OK` means the Agent system prompt is
  forcing that output. Create a normal Agent prompt for real model validation.
- If `pnpm` fails because the system Node is broken, use a Node `>=24 <25`
  runtime and put its `node` and `pnpm` binaries first in `PATH`.
