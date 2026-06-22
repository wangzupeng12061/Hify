from __future__ import annotations

from fastapi import FastAPI

from hify.bootstrap.container import HifyContainer, create_container


def create_app(container: HifyContainer | None = None) -> FastAPI:
    resolved_container = container or create_container()
    app = FastAPI(title="Hify API")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(resolved_container.identity.router)
    app.include_router(resolved_container.providers.router)
    return app


app = create_app()
