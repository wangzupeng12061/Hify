from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hify.modules.knowledge.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.knowledge.api.router import create_knowledge_router


class UnusedHandler:
    async def handle(self, command: Any = None, **kwargs: Any) -> Any:
        raise AssertionError("handler should not be called")


def test_knowledge_document_list_requires_configured_authentication() -> None:
    app = FastAPI()
    app.include_router(
        create_knowledge_router(
            create_knowledge_base_handler=UnusedHandler(),
            list_knowledge_bases_handler=UnusedHandler(),
            get_knowledge_base_handler=UnusedHandler(),
            list_knowledge_documents_handler=UnusedHandler(),
            ingest_document_handler=UnusedHandler(),
            request_authenticator=AuthenticationNotConfiguredAuthenticator(),
        )
    )
    client = TestClient(app)

    response = client.get("/knowledge-bases/00000000-0000-7000-8000-000000000010/documents")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_NOT_CONFIGURED"
