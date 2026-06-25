# Hify Phase-One Release Checklist

Use this checklist before opening Hify to a 50-100 person internal team.

## 1. Blocking Items

- [ ] Wire a real API authenticator for every module router. For small internal
  rollout, enable trusted header authentication only behind Cloudflare Access or
  an equivalent identity-aware reverse proxy that blocks direct origin access.
- [ ] Bootstrap the first administrator with `POST /auth/bootstrap/first-admin`
  and then remove `HIFY_AUTH_BOOTSTRAP_TOKEN` from the runtime environment.
- [ ] Configure production secret storage for the provider credential Fernet key.
  Never reuse the local example key.
- [ ] Confirm object storage settings and presigned upload flow before enabling
  document uploads for users.

## 2. Environment and Deployment

- [ ] Build `web`, `api`, and `worker` images from a clean checkout.
- [ ] Run Alembic migrations against an empty database.
- [ ] Verify PostgreSQL has `pgvector` enabled.
- [ ] Verify Redis uses authentication/TLS in production and `noeviction`.
- [ ] Confirm the reverse proxy strips `/api` before forwarding to FastAPI.
- [ ] Confirm proxy buffering is disabled for `/api/runs/*/execute-stream`.
- [ ] Confirm `/health/live` and `/health/ready` are used by the platform.
- [ ] Set `HIFY_DEPLOYMENT_MODE=production`,
  `HIFY_AUTH_DEV_LOGIN_ENABLED=false`, and
  `HIFY_AUTH_TRUSTED_HEADER_ENABLED=true` for trusted-header rollout.
- [ ] Confirm direct origin access is blocked before enabling trusted-header
  authentication.

## 3. Functional Smoke Test

- [ ] Bootstrap the owner user and team with a one-time bootstrap token.
- [ ] Verify a non-owner user can authenticate through the trusted email header
  and is added to the bootstrapped team as `member`.
- [ ] Configure one real provider credential and one chat model.
- [ ] Create and publish an Agent.
- [ ] Start a conversation and run the Agent through SSE.
- [ ] Create a knowledge base and verify RAG retrieval in a Run.
- [ ] Configure one HTTP tool and verify tool execution from a Run.
- [ ] Configure one MCP server and verify its tools appear in the Tools catalog.
- [ ] Create, publish, bind, and execute a simple Workflow.
- [ ] Verify Usage records token totals and cost estimate.
- [ ] Verify Run diagnostics shows failed provider/tool calls.

## 4. Operational Smoke Test

- [ ] Stop one API container while a run is active and verify the failure is
  visible as interrupted or failed, not stuck running.
- [ ] Stop Worker and verify API control-plane endpoints still respond.
- [ ] Stop Redis and verify background jobs fail visibly or degrade without
  corrupting database state.
- [ ] Point a provider at a failing endpoint and verify timeout/retry/error
  diagnostics are visible.
- [ ] Run `deploy/smoke-test.sh` against the public base URL after deployment.

## 5. Go / No-Go

Go only when all blocking items are closed and the functional smoke test passes
on the deployment environment. If any blocking item remains open, the system is
still in internal development mode even if all containers start successfully.
