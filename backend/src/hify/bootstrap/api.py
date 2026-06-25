from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text

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

    @app.get("/health/live")
    async def health_live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def health_ready() -> JSONResponse:
        checks: dict[str, str] = {
            "auth": "unknown",
            "database": "unknown",
            "provider_credential_encryption_key": "unknown",
            "redis": "unknown",
        }

        try:
            async with resolved_container.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "unavailable"

        if resolved_container.settings.provider_credential_encryption_key:
            checks["provider_credential_encryption_key"] = "ok"
        else:
            checks["provider_credential_encryption_key"] = "missing"

        checks["auth"] = _auth_health_status(resolved_container.settings)
        checks["redis"] = await _redis_health_status(resolved_container.settings.redis_url)

        if (
            checks["database"] != "ok"
            or checks["provider_credential_encryption_key"] != "ok"
            or checks["auth"] not in {"ok", "development"}
        ):
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "checks": checks},
            )

        status = "degraded" if checks["redis"] != "ok" else "ok"
        return JSONResponse(status_code=200, content={"status": status, "checks": checks})

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


def _auth_health_status(settings: object) -> str:
    deployment_mode = getattr(settings, "deployment_mode", "development")
    if deployment_mode != "production":
        return "development"
    if getattr(settings, "auth_dev_login_enabled", False):
        return "development_login_enabled"
    if getattr(settings, "auth_trusted_header_enabled", False):
        return "ok"
    if getattr(settings, "auth_oidc_enabled", False):
        return "oidc_not_implemented"
    return "missing"


async def _redis_health_status(redis_url: str) -> str:
    if not redis_url:
        return "not_configured"

    client = Redis.from_url(redis_url)
    try:
        await client.ping()
    except RedisError:
        return "degraded"
    finally:
        await client.aclose()

    return "ok"


app = create_app()
