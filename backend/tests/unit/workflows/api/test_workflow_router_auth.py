from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hify.modules.workflows.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.workflows.api.router import create_workflows_router


class UnusedHandler:
    async def handle(self, command: Any = None, **kwargs: Any) -> Any:
        raise AssertionError("handler should not be called")


def test_workflow_routes_require_configured_authentication() -> None:
    app = FastAPI()
    app.include_router(
        create_workflows_router(
            create_workflow_handler=UnusedHandler(),
            update_workflow_draft_handler=UnusedHandler(),
            publish_workflow_handler=UnusedHandler(),
            get_workflow_handler=UnusedHandler(),
            validate_workflow_draft_handler=UnusedHandler(),
            request_authenticator=AuthenticationNotConfiguredAuthenticator(),
        )
    )
    client = TestClient(app)

    response = client.post(
        "/workflows",
        json={
            "name": "Support Flow",
            "description": None,
            "draft_definition": {
                "nodes": [
                    {"id": "start", "kind": "start", "config": {}},
                    {"id": "end", "kind": "end", "config": {}},
                ],
                "edges": [{"source_node_id": "start", "target_node_id": "end"}],
            },
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_NOT_CONFIGURED"
