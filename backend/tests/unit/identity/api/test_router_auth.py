from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hify.modules.identity.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.identity.api.router import create_identity_router


class UnusedHandler:
    async def handle(self, command: Any) -> Any:
        raise AssertionError("handler should not be called")


def test_actor_routes_do_not_trust_client_supplied_identity_headers() -> None:
    app = FastAPI()
    app.include_router(create_identity_router(
        create_user_handler=UnusedHandler(),
        create_team_handler=UnusedHandler(),
        add_team_member_handler=UnusedHandler(),
        request_authenticator=AuthenticationNotConfiguredAuthenticator(),
    ))
    client = TestClient(app)

    response = client.get(
        "/identity/me",
        headers={
            "X-Hify-User-Id": "00000000-0000-7000-8000-000000000001",
            "X-Hify-Team-Id": "00000000-0000-7000-8000-000000000002",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_NOT_CONFIGURED"


def test_actor_routes_require_configured_authentication() -> None:
    app = FastAPI()
    app.include_router(create_identity_router(
        create_user_handler=UnusedHandler(),
        create_team_handler=UnusedHandler(),
        add_team_member_handler=UnusedHandler(),
        request_authenticator=AuthenticationNotConfiguredAuthenticator(),
    ))
    client = TestClient(app)

    response = client.get("/identity/me")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_NOT_CONFIGURED"
