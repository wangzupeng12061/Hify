# Hify Repository Instructions

This file applies to the entire repository. All AI agents and human contributors
must follow it when creating, reviewing, or modifying code.

## Read First

Before changing backend code, read:

1. `README.md`
2. `docs/architecture/code-organization.md`
3. The target module's existing code and tests

Before changing model-provider or agent-runtime code, also read
`docs/architecture/llm-api-resilience.md`.

Before changing deployment, networking, health checks, storage, or process
topology, also read `docs/architecture/deployment.md`.

Before changing concurrency, connection pools, queues, indexes, caching, or
capacity limits, also read `docs/architecture/capacity-bottlenecks.md`.

Before creating or changing tables, columns, indexes, queries, pagination,
retention, or migrations, also read
`docs/architecture/database-performance.md`.

The architecture document is mandatory. When this file and the architecture
document differ, follow the more restrictive rule. Do not create an exception
without updating the architecture document in the same change.

## Product Scope

Hify is an internal AI agent platform initially serving 50-100 users, with a
path to several thousand users. Its core capabilities are:

- Model provider and credential management
- Agent configuration and versioning
- Streaming conversations and agent runs
- Knowledge bases and RAG
- A simplified workflow definition and runtime
- Built-in, HTTP, and MCP tools
- Team access control, usage limits, and run diagnostics

Do not introduce Dify-scale features such as a plugin marketplace, arbitrary
code execution, multiple vector database adapters, or a general visual workflow
platform unless the task explicitly requires them.

## Technical Baseline

- Web: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query
- API: Python 3.12, FastAPI, Pydantic
- Agent runtime: LangGraph behind Hify-owned interfaces
- Persistence: PostgreSQL, pgvector, SQLAlchemy 2, Alembic
- Background jobs: Celery with Redis
- File storage: S3-compatible object storage
- Streaming: Server-Sent Events
- Packaging: `pnpm` for web and `uv` for Python
- Deployment: separate `web`, `api`, and `worker` containers

Do not replace a baseline component or add an overlapping framework without an
explicit architecture decision in `docs/architecture/`.

## Required Repository Shape

```text
apps/web/                         # Next.js application
backend/src/hify/bootstrap/       # Process startup and dependency wiring
backend/src/hify/modules/         # Business modules
backend/src/hify/shared/          # Business-neutral shared primitives
backend/tests/                    # Architecture, unit, integration, and E2E tests
backend/migrations/               # Alembic migrations
deploy/                           # Deployment configuration
docs/architecture/                # Architecture decisions and rules
```

Do not create global `controllers/`, `services/`, `models/`, `utils.py`, or
`helpers.py` directories/files for business code.

## Module Ownership

Place code in the module that owns the data and its state transitions:

| Module | Owns |
|---|---|
| `identity` | Users, teams, memberships, roles, permissions |
| `providers` | Model providers, model definitions, encrypted credentials |
| `agents` | Agent configuration, prompts, bindings, published versions |
| `conversations` | Conversations, messages, message feedback |
| `runs` | Executions, steps, stream events, cancellation, run status |
| `knowledge` | Knowledge bases, documents, chunks, embeddings, retrieval |
| `workflows` | Workflow definitions, nodes, edges, versions, validation |
| `tools` | Built-in and HTTP tool definitions, authorization, execution |
| `mcp` | MCP connections, discovery, MCP tool adaptation |
| `usage` | Token usage, quotas, costs, audit records |

If ownership is ambiguous, resolve it before writing code. Never duplicate the
same mutable data in two modules.

## Mandatory Module Layers

Every business module uses these layers:

```text
modules/<module>/
├── api/
├── application/
├── domain/
├── infrastructure/
├── contracts/
└── wiring.py
```

Create a directory only when it contains real code.

### Domain

- Contains entities, aggregates, value objects, domain services, events,
  domain errors, and repository protocols.
- May import only the Python standard library and `hify.shared.domain`.
- Must not import FastAPI, Pydantic, SQLAlchemy, Celery, Redis, LangGraph,
  LangChain, provider SDKs, or another business module.
- Must express mutations through domain methods, not public field assignment.

### Application

- Contains commands, queries, handlers, application DTOs, ports, and event
  handlers.
- Coordinates domain objects, repositories, units of work, and contracts.
- Must not import FastAPI, SQLAlchemy models/sessions, or third-party service
  SDKs.
- One public command or query per file. Use names such as
  `CreateAgentCommand`, `CreateAgentHandler`, and `GetAgentQuery`.

### API

- Contains FastAPI routers, dependencies, and Pydantic request/response schemas.
- Router functions only parse input, create a command/query, call a handler,
  and map the result.
- Must not query databases, control transactions, calculate business rules, or
  import infrastructure.
- Must never return SQLAlchemy models directly.

### Infrastructure

- Implements repositories, units of work, external adapters, queues, storage,
  database models, and background tasks.
- Converts third-party objects and failures into Hify DTOs and errors.
- Must not define business rules and must not be imported by another module.

### Contracts

- Is the module's only public import surface.
- Contains Protocols, immutable DTOs, versioned integration events, and stable
  public errors only.
- Contract DTOs use `@dataclass(frozen=True, slots=True)`.
- Must not export entities, ORM models, repositories, handlers, framework
  schemas, LangGraph state, or SDK types.

### Wiring

- Creates and connects repositories, adapters, and handlers for one module.
- May be imported only by `hify.bootstrap`.
- Business decisions do not belong in `wiring.py` or the dependency container.

## Import Rules

These rules are absolute:

1. A module may import another module only through
   `hify.modules.<other>.contracts`.
2. Domain code may not import any other business module, including contracts.
3. API may not import Infrastructure.
4. Application may not import ORM models, database sessions, FastAPI, or SDKs.
5. Another module may not import `wiring.py`.
6. `bootstrap` is the only package allowed to wire multiple module
   implementations together.
7. Circular imports, runtime imports used to hide a cycle, and `TYPE_CHECKING`
   used to bypass boundaries are prohibited.

## Cross-Module Calls

Use exactly one of these mechanisms:

### Synchronous read

- Define a Protocol and immutable result DTO in the provider module's
  `contracts`.
- Inject the implementation into the consumer's application handler.
- Never instantiate another module's handler or repository directly.

### Synchronous write

- Do not mutate another module inside the caller's transaction.
- Call an idempotent command contract only after the caller commits.
- Include a globally unique `idempotency_key` and define retry/compensation.
- Never share a SQLAlchemy Session between modules.

### Asynchronous side effect

- Publish a versioned event such as `AgentPublishedV1` through a transactional
  outbox.
- Consumers deduplicate by `event_id`.
- Create a new event version when field meaning or compatibility changes.

### Multi-module use case

- Put orchestration involving three or more modules in
  `hify.bootstrap.orchestrators`.
- Orchestrators call contracts only and must define idempotency, retry, and
  compensation. They do not access repositories or open cross-module
  transactions.

## Database Rules

- Prefix tables with the owner module, for example `agents_agents` and
  `runs_steps`.
- Repositories access only tables owned by their module.
- Cross-module references are scalar UUIDs.
- Cross-module ORM relationships, database foreign keys, and SQL joins are
  prohibited.
- Compose cross-module query results in application handlers through contracts,
  or maintain an event-driven local read model.
- Prefix migration filenames with the owner module.
- Every schema change requires an Alembic migration; never rely on ORM
  auto-creation in production.

## AI Runtime Boundaries

- `runs` owns execution lifecycle and is the only runtime orchestrator.
- LangGraph imports are restricted to
  `modules/runs/infrastructure/adapters/langgraph/`.
- Store Hify's versioned workflow JSON, not LangGraph objects, as the workflow
  source of truth.
- Provider SDK imports are restricted to
  `modules/providers/infrastructure/adapters/<provider>/`.
- MCP SDK imports are restricted to `modules/mcp/infrastructure/`.
- pgvector queries are restricted to `modules/knowledge/infrastructure/`.
- Interactive runs stream through a `RunExecutor` and Hify-defined `RunEvent`.
  Do not implement interactive runs as ordinary Celery tasks.
- Celery is for document parsing, embeddings, cleanup, statistics, and other
  retryable background work.

## Shared Code

Code may enter `hify.shared` only when all conditions are true:

1. At least three modules use it.
2. It has no business-module terminology.
3. It is a primitive such as IDs, clocks, pagination, event bus abstractions,
   session factories, logging, tracing, or encryption.

Otherwise keep it in the owner module. Do not move duplicated business logic to
`shared` merely to remove two imports.

## Frontend Boundaries

- The web app owns presentation and browser interaction only.
- Authorization, business rules, agent execution, and persistence stay in the
  backend.
- Generate the TypeScript API client from FastAPI OpenAPI. Do not maintain
  handwritten duplicate request/response types.
- Keep server state in TanStack Query. Use local component state for transient
  UI state; add global client state only when multiple unrelated routes need it.
- Treat Hify SSE events as the public streaming protocol. Do not expose
  LangGraph event objects to the browser.

## Coding Standards: 20 Mandatory Rules

These rules apply to every new or modified file. AI agents must enforce them
during implementation and review.

### Naming

1. **Use stable domain vocabulary.** Names must be English, describe one Hify
   concept, and use complete words. Only `id`, `api`, `url`, `http`, `llm`,
   `mcp`, `rag`, and `sse` are accepted abbreviations; do not invent local
   abbreviations.

2. **Follow language naming conventions.** Python modules, functions, methods,
   and variables use `snake_case`; classes use `PascalCase`; constants use
   `UPPER_SNAKE_CASE`. TypeScript variables and functions use `camelCase`;
   components, classes, and types use `PascalCase`; source filenames use
   `kebab-case`.

3. **Make type and quantity visible in the name.** Boolean names start with
   `is_`/`has_`/`can_` in Python and `is`/`has`/`can` in TypeScript. Collections
   use plural nouns. Numeric values with units include the unit, such as
   `timeout_seconds`, `duration_ms`, and `size_bytes`.

4. **Name actions by their observable effect.** Commands and mutating functions
   use explicit verbs such as `create_agent`, `publish_agent`, or
   `cancel_run`; queries use `get`, `list`, `find`, or `exists`. Do not hide
   writes behind names such as `get`, `check`, or `process`.

5. **Reject vague containers.** Do not introduce business symbols named
   `manager`, `helper`, `utils`, `common`, `data`, `info`, `processor`, or
   `handler` without a specific domain qualifier. Prefer names such as
   `RunCancellationService` or `ProviderRetryPolicy`.

### Exceptions

6. **Raise typed, stable errors.** Expected failures use the owning module's
   error type with an `Error` suffix and a stable machine-readable `error_code`.
   Do not raise generic `Exception`, strings, HTTP errors, or provider SDK
   errors from Domain/Application code.

7. **Catch only errors that can be handled.** Every `except`/`catch` must retry,
   translate, compensate, or add required boundary context. Bare catches and
   `except Exception` are prohibited outside process, API, task, and adapter
   boundaries; TypeScript catch values are treated as `unknown`, not `any`.

8. **Preserve the cause while translating.** Python uses
   `raise HifyError(...) from exc`; TypeScript uses `new HifyError(..., {
   cause: error })`. Keep the original cause for logs and traces, but return only
   stable Hify error codes and safe messages to callers.

9. **Never swallow cancellation or timeout.** Cancellation is re-raised after
   cleanup and is not converted into a provider failure. Timeout errors must
   identify the stage and remain distinct from cancellation, validation, and
   availability errors.

10. **Use errors only for exceptional outcomes.** Expected absence returns
    `None`/`null` only when the function contract names that possibility.
    Validation conflicts, quota failures, and state-transition failures use
    explicit typed errors; do not use sentinel strings, magic booleans, or
    partially populated DTOs.

### Logging

11. **Emit structured logs through the module logger.** Python uses
    `logger = logging.getLogger(__name__)`; TypeScript uses the repository logger.
    Production code must not use `print`, `console.log`, or manually formatted
    JSON strings.

12. **Use stable event names and correlation fields.** Every operational log has
    a lowercase dot-separated `event` such as `run.started` and includes all
    available identifiers from `request_id`, `run_id`, `attempt_id`, `job_id`,
    `team_id`, `provider`, and `model`. Do not put identifiers only inside the
    free-text message.

13. **Apply log levels consistently.** `DEBUG` is local diagnostic detail;
    `INFO` is a completed lifecycle transition; `WARNING` is a recovered or
    degraded condition; `ERROR` is a failed operation requiring attention;
    `CRITICAL` is process-wide or data-integrity failure. Normal retries and
    expected 4xx responses are not `ERROR`.

14. **Never log secrets or unbounded payloads.** API keys, Authorization/Cookie
    headers, encrypted credentials, full prompts, model responses, document
    contents, tool arguments, and personal data are prohibited. Log hashes,
    byte/token counts, approved metadata, and truncated safe error summaries.

15. **Log a failure once at its handling boundary.** Lower layers translate and
    propagate; the API/task/process boundary records the final outcome. Use
    stack traces only for unexpected failures (`logger.exception` in Python);
    do not log and re-raise the same failure at every layer.

### Concurrency

16. **Keep the Event Loop non-blocking.** Interactive paths use async network and
    database clients. Blocking or CPU-heavy work goes to Celery; a temporarily
    unavoidable sync call uses `anyio.to_thread.run_sync` with the repository's
    bounded `CapacityLimiter`, never the unrestricted default thread pool.

17. **Bound every source of concurrency and buffering.** Fan-out uses a named
    Semaphore or queue with an explicit limit, acquisition timeout, and overload
    result. Do not pass an unbounded collection to `gather`, create an unbounded
    queue, or start work before capacity is acquired.

18. **Give every task an owner and lifecycle.** Prefer `asyncio.TaskGroup` for
    child tasks. Do not call `asyncio.create_task` or its TypeScript equivalent
    without storing the task in an owner registry, observing its exception, and
    cancelling/awaiting it during owner shutdown.

19. **Propagate one deadline and cancellation signal.** Derive child timeouts
    from the remaining parent deadline. On cancellation, stop retry sleeps,
    close upstream streams, release Semaphores/leases/sessions in `finally`, and
    persist the terminal state. Do not shield work except for short bounded
    cleanup.

20. **Use distributed correctness primitives.** In-process locks protect only
    one process and must not enforce cross-replica invariants. Use database
    constraints/optimistic versions for durable state and Redis leases with an
    owner token plus TTL for temporary coordination. Never hold a database
    transaction or lock while awaiting LLM, MCP, HTTP, S3, or queue I/O; all
    retried side effects require an idempotency key.

## Implementation Procedure

For every code task:

1. Identify the owner module and layer before editing.
2. Inspect existing contracts, domain rules, migrations, and tests.
3. Add or change the smallest stable contract required by consumers.
4. Implement domain behavior without frameworks.
5. Implement the application command/query and ports.
6. Implement infrastructure adapters and API mapping last.
7. Wire dependencies in the module's `wiring.py` and `bootstrap/container.py`.
8. Add tests at the appropriate layer.
9. Run architecture checks, targeted tests, then the full relevant suite.
10. Report anything that could not be verified.

Do not introduce speculative abstractions, compatibility shims for unused code,
or unrelated refactors.

## Testing and Verification

Required test level by change:

- Domain behavior: pure unit test with no external dependencies.
- Application handler: unit test with fake contracts and repositories.
- Repository or adapter: integration test against the real dependency or its
  official test container.
- API route: contract test with application handlers replaced.
- Cross-module flow: integration test that calls contracts only.

When the corresponding projects exist, run:

```bash
cd backend
uv run python scripts/check_architecture.py
uv run pytest tests/architecture
uv run pytest

cd ../apps/web
pnpm lint
pnpm type-check
pnpm test
```

Do not claim verification for commands that were not run. If scaffolding is not
yet present, state that clearly instead of inventing successful results.

## Completion Checklist

Before finishing, verify:

- The owner module and layer are correct.
- Cross-module imports stop at `contracts`.
- No framework or SDK type leaks into Domain or Contracts.
- No repository touches another module's table.
- Events are versioned and consumers are idempotent.
- API and database migrations are backward-safe where required.
- New behavior has tests at the correct layer.
- Architecture checks and relevant test suites pass.
