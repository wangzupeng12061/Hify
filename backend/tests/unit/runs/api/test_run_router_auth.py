from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hify.modules.runs.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.runs.api.router import create_runs_router


class UnusedHandler:
    async def handle(self, command: Any) -> Any:
        raise AssertionError("handler should not be called")


def test_run_routes_require_configured_authentication() -> None:
    app = FastAPI()
    app.include_router(
        create_runs_router(
            create_run_handler=UnusedHandler(),
            cancel_run_handler=UnusedHandler(),
            get_run_handler=UnusedHandler(),
            list_events_handler=UnusedHandler(),
            run_executor=UnusedHandler(),
            request_authenticator=AuthenticationNotConfiguredAuthenticator(),
        )
    )
    client = TestClient(app)

    response = client.post(
        "/runs",
        json={
            "conversation_id": "00000000-0000-7000-8000-000000000001",
            "idempotency_key": "run-1",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_NOT_CONFIGURED"


def test_run_stream_route_requires_configured_authentication() -> None:
    app = FastAPI()
    app.include_router(
        create_runs_router(
            create_run_handler=UnusedHandler(),
            cancel_run_handler=UnusedHandler(),
            get_run_handler=UnusedHandler(),
            list_events_handler=UnusedHandler(),
            run_executor=UnusedHandler(),
            request_authenticator=AuthenticationNotConfiguredAuthenticator(),
        )
    )
    client = TestClient(app)

    response = client.post(
        "/runs/00000000-0000-7000-8000-000000000001/execute-stream",
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_NOT_CONFIGURED"
