---
applyTo: "**"
---

# Hify Code Review Instructions

## Review Objective

- Report only actionable defects introduced or exposed by the pull request.
- Prioritize correctness, security, data integrity, concurrency, reliability,
  performance, and architectural boundary violations over style preferences.
- Review changed code in its repository context. Check related contracts,
  callers, migrations, tests, dependency manifests, lockfiles, and architecture
  documents before concluding that a change is defective.
- Do not report speculative issues without a realistic trigger and observable
  impact. Do not report formatting or naming issues already enforced by
  automated tools unless they create a functional defect.
- Do not praise unchanged or correct code. If no actionable issue exists, leave
  no inline comment.

## Finding Quality

- Anchor each finding to the smallest relevant changed line range.
- State the concrete trigger, resulting impact, and a viable correction
  direction.
- Treat security vulnerabilities, authorization bypasses, credential exposure,
  data loss, and production outages as critical.
- Treat incorrect behavior, race conditions, broken public contracts, failed
  migrations, and unrecoverable jobs as high priority.
- Treat reproducible performance, resource, observability, or maintainability
  problems as medium priority only when they have a plausible production path.
- Avoid duplicate findings. When one root cause affects multiple locations,
  comment on the root cause and mention the affected behavior.

## Repository Architecture

- Enforce the ownership and dependency rules in `AGENTS.md` and
  `docs/architecture/code-organization.md`.
- A business module may import another business module only through the
  provider module's `contracts`, and only when allowed by the synchronous
  dependency allowlist.
- Domain code may depend only on the standard library and
  `hify.shared.domain`. Flag framework, ORM, SDK, queue, or cross-module imports.
- API code must remain a thin adapter. Flag database access, transaction
  control, authorization rules, or business decisions in routers.
- Application code must not import FastAPI, SQLAlchemy models or sessions, or
  third-party SDKs.
- Infrastructure must not be imported by another module or contain business
  rules.
- Multi-module writes must use a Process Manager or Saga with idempotency,
  retry, and compensation. Flag shared SQLAlchemy sessions or cross-module
  transactions.
- Repositories may access only tables owned by their module. Flag cross-module
  joins, ORM relationships, foreign keys, or direct table writes.

## Runtime And Reliability

- For LLM, embedding, HTTP tool, MCP, S3, Redis, and provider SDK calls, verify
  bounded timeouts, cancellation behavior, retry eligibility, idempotency, and
  typed error translation.
- Flag retries for authentication failures, validation failures, policy
  failures, context-length errors, or other permanent errors.
- Flag unbounded concurrency, per-request client creation, blocking I/O on the
  async API event loop, and network calls held inside database transactions.
- Interactive agent runs must use the Hify `RunExecutor` and SSE event protocol,
  not ordinary Celery tasks or raw LangGraph events.
- Background jobs and event consumers must tolerate at-least-once delivery.
  Verify stable idempotency keys, Inbox or deduplication handling, leases, and
  safe retries.
- Ensure the documented Celery queue names and responsibilities remain
  consistent across deployment, resilience, and capacity documents.

## Security And Data

- Flag hardcoded secrets, plaintext provider credentials, sensitive data in
  logs, unsafe URL fetching, missing tenant scoping, and authorization checks
  performed only in the frontend.
- Every user-facing operation must carry an authenticated `ActorContext`; the
  owning module's Application layer must enforce operation-specific
  authorization.
- Verify SQL is parameterized and all list, update, and delete queries are
  scoped by the owning team or tenant where applicable.
- Schema changes must include an Alembic migration and remain backward-safe for
  rolling deployment. Check indexes, uniqueness, nullability, defaults,
  retention, and pagination against
  `docs/architecture/database-performance.md`.
- Business IDs use the shared UUIDv7 factory. Flag UUIDv4, serial identifiers,
  or direct UUID-library calls in business code.

## Frontend

- `src/app` contains routing and composition only. Reusable product behavior
  belongs in `src/features`.
- Features may import another feature only through its public `index.ts`.
  Client Components must not import `src/lib/server`.
- API request and response types come from the generated OpenAPI client. Flag
  handwritten duplicate transport types or exposure of LangGraph events.
- Authorization and business invariants must remain in the backend.

## Tests And Configuration

- Require focused tests for changed behavior: pure Domain tests, Application
  tests with fakes, Infrastructure integration tests, API contract tests, and
  cross-module flow tests as appropriate.
- Flag tests that assert implementation details while missing the changed
  behavior, failure path, concurrency path, or tenant boundary.
- When dependencies change, require the matching lockfile update and verify
  compatibility with Python 3.12, Node.js, `uv`, and `pnpm`.
- Keep documentation, dependency manifests, queue definitions, and deployment
  topology consistent. Treat contradictions that can cause implementation or
  operational misconfiguration as defects.
- Empty package files and placeholders are intentional during scaffolding. Do
  not report them unless the pull request claims the corresponding component is
  executable or production-ready.
