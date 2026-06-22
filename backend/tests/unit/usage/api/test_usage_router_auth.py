from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hify.modules.usage.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.usage.api.router import create_usage_router


class UnusedHandler:
    async def handle(self, command: Any) -> Any:
        raise AssertionError("handler should not be called")


def test_usage_routes_require_configured_authentication() -> None:
    app = FastAPI()
    app.include_router(
        create_usage_router(
            get_team_summary_handler=UnusedHandler(),
            get_run_summary_handler=UnusedHandler(),
            request_authenticator=AuthenticationNotConfiguredAuthenticator(),
        )
    )
    client = TestClient(app)

    response = client.get("/usage/summary")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_NOT_CONFIGURED"
