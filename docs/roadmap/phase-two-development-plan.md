# Hify Phase Two Development Plan

This document defines the second-stage development plan after the phase-one
small real-use rollout. Architecture boundaries remain defined by
`docs/architecture/`; this document only defines delivery order, acceptance
criteria, and scope control.

## 1. Phase Goal

Phase two moves Hify from "small internal real use" to "repeatable team
adoption and stronger general-agent capability".

Target outcome:

- A normal team can create, publish, and use useful agents without developer
  assistance.
- Agents can use approved tools, search the web through Hify-owned tool
  integrations, retrieve knowledge with visible sources, and show execution
  progress.
- Operators can diagnose failures, control spend, back up data, and deploy with
  repeatable scripts.
- The system stays simple enough for one developer to maintain while leaving a
  path to several thousand users.

## 2. Non-Goals

Do not build these in phase two unless a separate architecture decision is
approved:

- Public marketplace, plugin store, or third-party extension distribution.
- Arbitrary user code execution or browser/computer automation sandboxes.
- Multiple vector database adapters.
- Full visual workflow platform comparable to Dify or Zapier.
- Multi-tenant billing product, public signup, or external customer isolation.
- Kubernetes migration.

## 3. Stage Principles

Every phase-two task must follow these rules:

1. Keep the domain modular monolith. Cross-module imports must use Contracts
   only and follow the allowlist in `AGENTS.md`.
2. Prefer one feature vertical slice per PR: backend contract, API, generated
   client update, frontend UI, tests, and docs when needed.
3. Build Hify-owned abstractions before integrating provider SDK behavior into
   business logic.
4. Keep production defaults safe: trusted-header auth requires private origin
   ports, tools require allowlists, and secrets never enter logs.
5. A feature is not complete until it has a smoke path that a human can run
   against the online environment.

## 4. Milestones

### Milestone 2.1: General Agent Tooling

Goal: make the default Agent visibly capable of multi-step tool use.

Must deliver:

- Web search as a built-in Tool owned by `tools`.
- Tool authorization and execution policy visible in Agent configuration.
- Runs Tool Loop improvements: tool selection, tool result injection, repeated
  tool calls, max-step protection, cancellation, and failure diagnostics.
- Frontend rendering for tool-call lifecycle: requested, running, succeeded,
  failed, skipped.
- Online smoke test: ask a current-events question, show that the Agent used web
  search, and record the result in conversation history.

Module ownership:

| Capability | Owner |
|---|---|
| Tool catalog and web-search tool definition | `tools` |
| External search adapter | `tools.infrastructure` |
| Runtime orchestration | `runs` |
| Agent-level tool binding | `agents` |
| UI configuration and event rendering | `apps/web/src/features/agents`, `apps/web/src/features/conversations` |

Acceptance criteria:

- A published Agent can be bound to web search without direct database edits.
- Tool calls are persisted as Run steps and visible from diagnostics.
- Tool failures do not leave Runs stuck in `running`.
- Public API does not expose provider SDK or search-provider response objects.

### Milestone 2.2: Knowledge Ingestion and RAG Quality

Goal: make knowledge bases usable with real uploaded documents.

Must deliver:

- Object storage settings and presigned upload flow.
- Document ingestion Jobs: upload confirmation, parsing, chunking, embedding,
  retry, and failure visibility.
- RAG source display in chat: document title, chunk preview, and relevance
  score where available.
- Knowledge binding UX for Agents with clear published-version behavior.
- Online smoke test: upload a document, wait for indexing, ask a question, and
  verify cited sources appear.

Module ownership:

| Capability | Owner |
|---|---|
| Knowledge base, documents, chunks, retrieval | `knowledge` |
| Durable parsing and embedding work | `jobs` |
| Provider model calls for embeddings | `providers` |
| Agent knowledge binding | `agents` |
| RAG injection into Run context | `runs` |

Acceptance criteria:

- Uploads do not pass large file bodies through API containers.
- Ingestion can be retried idempotently.
- Retrieval stays inside `knowledge.infrastructure`.
- Conversation history preserves enough metadata to explain used sources.

### Milestone 2.3: Workflow Runtime Usability

Goal: make simplified workflows useful as Agent execution plans.

Must deliver:

- First practical node set: prompt, model call, tool call, knowledge retrieval,
  condition, and final response.
- Workflow validation errors returned as stable API errors.
- Workflow run visualization in the user chat and admin diagnostics.
- Agent binding to a published Workflow version with immutable snapshots.
- Online smoke test: bind an Agent to a workflow that retrieves knowledge and
  calls one tool.

Module ownership:

| Capability | Owner |
|---|---|
| Workflow definitions, versions, validation | `workflows` |
| Agent workflow binding | `agents` |
| Runtime execution | `runs` |
| Tool execution | `tools` |
| UI editor and runtime display | `apps/web/src/features/workflows`, `apps/web/src/features/conversations` |

Acceptance criteria:

- Runtime reads versioned Hify workflow JSON, not LangGraph objects.
- Workflow execution cannot mutate workflow definitions.
- Each node execution is persisted as a Run step.
- A failed node produces a diagnosable terminal Run state.

### Milestone 2.4: Team Governance and Operations

Goal: make Hify manageable by a small internal platform owner.

Must deliver:

- Role and permission checks for admin pages and mutating APIs.
- Audit records for provider credentials, Agent publish, tool changes, budget
  changes, and user-role changes.
- Usage budget views by team, provider, model, Agent, and user.
- Budget warning and hard-stop policy for phase-two usage limits.
- Operational runbook updates for backup restore drill and release smoke tests.

Module ownership:

| Capability | Owner |
|---|---|
| Users, roles, memberships, permissions | `identity` |
| Cost and quota accounting | `usage` |
| Audit records | owning module or `usage` when cost-related |
| Admin UI | relevant `apps/web/src/features/*` |

Acceptance criteria:

- A non-admin cannot access admin-only API mutations.
- Budget enforcement is deterministic and tested at application-handler level.
- Audit records never include secrets, prompts, full responses, or credentials.

### Milestone 2.5: Scale and Reliability Readiness

Goal: remove the largest blockers before expanding beyond a small pilot team.

Must deliver:

- Queue separation for ingestion, embedding, maintenance, and event tasks.
- Operational dashboards or documented log queries for API, worker, run, job,
  provider, and tool failures.
- Backup restore drill documented with evidence.
- Database slow-query review and missing-index cleanup for large tables.
- CI workflow that runs architecture checks, backend tests, web lint,
  type-check, and tests.

Acceptance criteria:

- Repeated provider failures produce visible diagnostics and do not exhaust API
  capacity.
- Worker failures are recoverable from durable Jobs.
- Deployment and rollback scripts are documented and tested after one release.
- Database connection budgets remain within limits defined in
  `docs/architecture/deployment.md`.

## 5. Recommended Delivery Order

Use this order unless a production incident changes priority:

1. Web search built-in Tool and Tool Loop hardening.
2. Frontend tool-call event rendering.
3. Object storage and document upload ingestion.
4. RAG source display and retrieval quality pass.
5. Workflow node execution improvements.
6. Admin permissions and audit records.
7. Usage budget enforcement refinements.
8. CI and operational restore drill.

Each item should land as one or more small PRs. Do not combine unrelated
milestones in the same PR.

## 6. Definition of Done

A phase-two feature is done only when all applicable items are true:

- Owner module and layer are correct.
- Public cross-module surface is in `contracts`.
- API schema is stable and OpenAPI client is regenerated when changed.
- Frontend uses generated API types and TanStack Query for server state.
- Unit or integration tests cover the changed behavior.
- Architecture checks pass.
- The feature has a documented local or online smoke path.
- Any new operational risk is reflected in `docs/operations/` or
  `deploy/cloudlab/`.

## 7. Phase-Two Exit Criteria

Phase two is complete when:

- At least one production Agent can answer current-information questions using
  web search with visible tool trace.
- At least one production Agent can answer from uploaded internal documents
  with visible RAG sources.
- At least one production Agent can run a published workflow with persisted node
  steps.
- Admin-only changes are permission-protected and audited.
- Usage budget views and enforcement are reliable enough for a several-team
  pilot.
- Online deployment has repeatable backup, restore, deploy, rollback, and smoke
  procedures.
