from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hify.modules.mcp.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.mcp.api.router import create_mcp_router


class UnusedHandler:
    async def handle(self, command: Any = None, **kwargs: Any) -> Any:
        raise AssertionError("handler should not be called")


def test_mcp_routes_require_configured_authentication() -> None:
    app = FastAPI()
    app.include_router(
        create_mcp_router(
            create_server_handler=UnusedHandler(),
            get_server_handler=UnusedHandler(),
            list_servers_handler=UnusedHandler(),
            list_tools_handler=UnusedHandler(),
            refresh_tools_handler=UnusedHandler(),
            request_authenticator=AuthenticationNotConfiguredAuthenticator(),
        )
    )
    client = TestClient(app)

    response = client.post(
        "/mcp/servers",
        json={
            "name": "Docs",
            "description": None,
            "transport": "streamable_http",
            "endpoint_url": "https://mcp.example.com/mcp",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_NOT_CONFIGURED"
