from __future__ import annotations

from fastapi import FastAPI

from hify.bootstrap.api_schemas import DEFAULT_ERROR_RESPONSES, generate_operation_id
from hify.bootstrap.container import HifyContainer, create_container


def create_app(container: HifyContainer | None = None) -> FastAPI:
    resolved_container = container or create_container()
    app = FastAPI(
        title="Hify API",
        version="0.1.0",
        responses=DEFAULT_ERROR_RESPONSES,
        generate_unique_id_function=generate_operation_id,
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(resolved_container.identity.router)
    app.include_router(resolved_container.providers.router)
    app.include_router(resolved_container.agents.router)
    app.include_router(resolved_container.conversations.router)
    app.include_router(resolved_container.jobs.router)
    app.include_router(resolved_container.knowledge.router)
    app.include_router(resolved_container.mcp.router)
    app.include_router(resolved_container.runs.router)
    app.include_router(resolved_container.tools.router)
    app.include_router(resolved_container.usage.router)
    app.include_router(resolved_container.workflows.router)
    return app


app = create_app()
