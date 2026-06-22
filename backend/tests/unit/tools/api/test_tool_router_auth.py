from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hify.modules.tools.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.tools.api.router import create_tools_router


class UnusedHandler:
    async def handle(self, command: Any = None, **kwargs: Any) -> Any:
        raise AssertionError("handler should not be called")


def test_tool_routes_require_configured_authentication() -> None:
    app = FastAPI()
    app.include_router(
        create_tools_router(
            create_tool_handler=UnusedHandler(),
            get_tool_handler=UnusedHandler(),
            list_tools_handler=UnusedHandler(),
            request_authenticator=AuthenticationNotConfiguredAuthenticator(),
        )
    )
    client = TestClient(app)

    response = client.post(
        "/tools",
        json={
            "name": "Search",
            "description": None,
            "tool_kind": "builtin",
            "input_schema": {"type": "object"},
            "builtin_name": "web.search",
            "endpoint_url": None,
            "http_method": None,
            "http_headers": {},
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_NOT_CONFIGURED"
