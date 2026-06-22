from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hify.modules.conversations.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.conversations.api.router import create_conversations_router


class UnusedHandler:
    async def handle(self, command: Any) -> Any:
        raise AssertionError("handler should not be called")


def test_conversation_routes_require_configured_authentication() -> None:
    app = FastAPI()
    app.include_router(
        create_conversations_router(
            create_conversation_handler=UnusedHandler(),
            append_message_handler=UnusedHandler(),
            list_messages_handler=UnusedHandler(),
            submit_feedback_handler=UnusedHandler(),
            request_authenticator=AuthenticationNotConfiguredAuthenticator(),
        )
    )
    client = TestClient(app)

    response = client.post(
        "/conversations",
        json={
            "agent_id": "00000000-0000-7000-8000-000000000001",
            "title": "Support",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_NOT_CONFIGURED"
