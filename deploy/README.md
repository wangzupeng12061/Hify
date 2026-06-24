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

5. Open the web app:

   ```text
   http://localhost:8080
   ```

## Production Notes

- Run `migration` as a one-shot job before rolling API and Worker containers.
- Expose only the reverse proxy or platform load balancer to the public network.
- Keep PostgreSQL, Redis, Worker, and any Ollama host private.
- Disable proxy buffering for `/api/runs/*/execute-stream`.
- Use managed PostgreSQL with pgvector, managed Redis, and managed object
  storage where available.
- Store real secrets in the platform secret manager, not in `.env`.

## Known Release Blockers

- Business API routers still use the placeholder authenticator. A production
  release must wire a real authenticator that resolves
  `identity.contracts.ActorContext`.
- Object storage presigned upload configuration is not represented in settings
  yet. Keep RAG smoke tests to flows currently implemented by the backend until
  storage settings are added.
