# Hify Phase-One Release Checklist

Use this checklist before opening Hify to a 50-100 person internal team.

## 1. Blocking Items

- [ ] Wire a real API authenticator for every module router. Placeholder
  `AuthenticationNotConfiguredAuthenticator` is acceptable for development only.
- [ ] Define the first-admin bootstrap path: create the first user, team,
  owner membership, and initial permissions without opening public self-service
  writes.
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

## 3. Functional Smoke Test

- [ ] Create or bootstrap a user and team.
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
