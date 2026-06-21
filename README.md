# Hify

Hify is a lightweight AI agent platform for internal teams of 50-100 users.
It uses a Python agent runtime and a TypeScript web application while keeping
the first production deployment intentionally small.

## Technical baseline

Backend code must follow the [modular monolith organization rules](docs/architecture/code-organization.md).
External model calls must follow the [LLM API resilience rules](docs/architecture/llm-api-resilience.md).
Production topology must follow the [initial deployment architecture](docs/architecture/deployment.md).
Capacity work must use the [phase-one bottleneck analysis](docs/architecture/capacity-bottlenecks.md).
Database changes must follow the [database performance rules](docs/architecture/database-performance.md).

### Web

- Next.js, React, and TypeScript
- Tailwind CSS and shadcn/ui
- TanStack Query for server state
- Generated TypeScript client from the backend OpenAPI specification

The web application owns presentation and browser interaction. Business rules,
authorization, agent execution, and data access remain in the backend.

### Backend

- Python 3.12
- FastAPI and Pydantic
- SQLAlchemy 2 and Alembic
- Server-Sent Events (SSE) for agent response streaming

FastAPI is the system API and the sole owner of authentication, authorization,
business logic, and persistence. In production, the web and API are exposed
under one origin through a reverse proxy.

### Agent and knowledge runtime

- LangGraph for stateful agent execution
- LangChain model integrations behind Hify-owned provider interfaces
- PostgreSQL with pgvector for document and vector storage
- Object storage with an S3-compatible API for uploaded files

Agent runs emit a Hify-defined event protocol so the runtime can evolve without
coupling the web application to LangGraph-specific data structures.

### Background processing

- Celery workers for document parsing, embedding, and maintenance jobs
- Redis as the Celery broker and short-lived cache

Interactive agent runs stream directly from FastAPI. Slow or retryable work is
submitted to workers and is never executed as an in-process background task.

### Operations

- Docker images for `web`, `api`, and `worker`
- PostgreSQL and Redis as managed services where possible
- Structured JSON logs, OpenTelemetry instrumentation, and Sentry
- Database migrations run as an explicit deployment step

## Initial deployment

```text
Browser
   |
Reverse Proxy
   |-- Next.js Web
   `-- FastAPI API -- PostgreSQL + pgvector
            |       `-- S3-compatible object storage
            |
            `-- Redis -- Celery Worker
                         `-- document parsing and embedding
```

## MVP boundaries

The first release includes agent configuration, chat, controlled tool calling,
basic RAG, run logs, team access control, and usage limits.

The first release does not include a visual workflow editor, plugin marketplace,
arbitrary code execution, multiple vector database adapters, or a general-purpose
workflow engine beyond the agent runtime.
