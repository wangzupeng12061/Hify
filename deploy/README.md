# Hify Phase-One Deployment

This directory contains the minimum deployment assets for phase-one release
verification. It is intended for a single host or ordinary container platform,
not Kubernetes.

## Local Release Verification

1. Create the environment file:

   ```bash
   cp .env.example .env
   ```

2. Replace `HIFY_PROVIDER_CREDENTIAL_ENCRYPTION_KEY` before any shared or
   production deployment.

3. Build and start the stack:

   ```bash
   docker compose -f deploy/docker-compose.yml --env-file .env up --build
   ```

4. Run smoke checks:

   ```bash
   deploy/smoke-test.sh http://localhost:8080
   ```

   For a real provider and browser chat verification path, also run the
   [local DeepSeek smoke test](../docs/operations/local-deepseek-smoke-test.md).

5. Open the web app:

   ```text
   http://localhost:8080
   ```

## Production Notes

- The current three-node CloudLab production rollout is documented and
  automated under `deploy/cloudlab/`.
- Run `migration` as a one-shot job before rolling API and Worker containers.
- Expose only the reverse proxy or platform load balancer to the public network.
- Set `HIFY_DEPLOYMENT_MODE=production`.
- Set `HIFY_AUTH_DEV_LOGIN_ENABLED=false`.
- For the first small internal rollout, put Hify behind Cloudflare Access or an
  equivalent identity-aware reverse proxy and set
  `HIFY_AUTH_TRUSTED_HEADER_ENABLED=true`.
- Keep direct origin access blocked when trusted-header authentication is
  enabled. Do not trust client-supplied identity headers from the public
  internet.
- Keep PostgreSQL, Redis, Worker, and any Ollama host private.
- Disable proxy buffering for `/api/runs/*/execute-stream`.
- Use managed PostgreSQL with pgvector, managed Redis, and managed object
  storage where available.
- Store real secrets in the platform secret manager, not in `.env`.

## First Administrator Bootstrap

Set a high-entropy `HIFY_AUTH_BOOTSTRAP_TOKEN` only for initial setup, deploy
the API, then call:

```bash
curl -i https://hify.example.com/api/auth/bootstrap/first-admin \
  -H "Authorization: Bearer ${HIFY_AUTH_BOOTSTRAP_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","display_name":"Owner","team_name":"Hify"}'
```

After the response sets the `hify_session` cookie and the owner exists, remove
`HIFY_AUTH_BOOTSTRAP_TOKEN` from the runtime environment and redeploy. Later
users should authenticate through the configured trusted identity header and are
added to the bootstrapped team with `HIFY_AUTH_TRUSTED_DEFAULT_ROLE`.

## Known Release Blockers

- Full OIDC authorization-code login is still not implemented. Use the
  trusted-header mode only behind Cloudflare Access or an equivalent
  identity-aware proxy for the first small rollout.
- Object storage presigned upload configuration is not represented in settings
  yet. Keep RAG smoke tests to flows currently implemented by the backend until
  storage settings are added.
