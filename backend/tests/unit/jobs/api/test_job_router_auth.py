from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hify.modules.jobs.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.jobs.api.router import create_jobs_router


class UnusedHandler:
    async def handle(self, command: Any) -> Any:
        raise AssertionError("handler should not be called")


def test_job_routes_require_configured_authentication() -> None:
    app = FastAPI()
    app.include_router(
        create_jobs_router(
            get_job_handler=UnusedHandler(),
            request_authenticator=AuthenticationNotConfiguredAuthenticator(),
        )
    )
    client = TestClient(app)

    response = client.get("/jobs/00000000-0000-7000-8000-000000000001")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_NOT_CONFIGURED"
