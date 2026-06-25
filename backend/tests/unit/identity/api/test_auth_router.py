from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hify.modules.identity.api.auth_router import AuthRouterConfig, create_auth_router
from hify.modules.identity.application.dto import AuthSessionResult
from hify.modules.identity.contracts.dto import ActorContext


class FakeCreateDevSessionHandler:
    async def handle(self, command: object) -> AuthSessionResult:
        return AuthSessionResult(
            token="dev-session-token",
            actor=create_actor(),
            expires_at=datetime(2026, 6, 30, tzinfo=UTC),
        )


class FakeBootstrapFirstAdminHandler:
    async def handle(self, command: object) -> AuthSessionResult:
        return AuthSessionResult(
            token="bootstrap-session-token",
            actor=create_actor(),
            expires_at=datetime(2026, 6, 30, tzinfo=UTC),
        )


class FakeRevokeSessionHandler:
    def __init__(self) -> None:
        self.tokens: list[str] = []

    async def handle(self, command: object) -> None:
        self.tokens.append(command.token)


class StaticAuthenticator:
    async def authenticate(self, request: object) -> ActorContext:
        return create_actor()


def test_dev_session_sets_http_only_cookie() -> None:
    revoke_handler = FakeRevokeSessionHandler()
    client = TestClient(create_test_app(revoke_handler=revoke_handler))

    response = client.post("/auth/dev/session", json={})

    assert response.status_code == 201
    assert response.json()["actor"]["role"] == "owner"
    set_cookie = response.headers["set-cookie"]
    assert "hify_session=dev-session-token" in set_cookie
    assert "HttpOnly" in set_cookie


def test_bootstrap_first_admin_requires_configured_token() -> None:
    revoke_handler = FakeRevokeSessionHandler()
    client = TestClient(create_test_app(revoke_handler=revoke_handler, bootstrap_token=None))

    response = client.post(
        "/auth/bootstrap/first-admin",
        json={
            "email": "owner@example.com",
            "display_name": "Owner",
            "team_name": "Hify",
        },
        headers={"Authorization": "Bearer bootstrap-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "IDENTITY_BOOTSTRAP_DISABLED"


def test_bootstrap_first_admin_rejects_invalid_token() -> None:
    revoke_handler = FakeRevokeSessionHandler()
    client = TestClient(create_test_app(revoke_handler=revoke_handler))

    response = client.post(
        "/auth/bootstrap/first-admin",
        json={
            "email": "owner@example.com",
            "display_name": "Owner",
            "team_name": "Hify",
        },
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "IDENTITY_BOOTSTRAP_FORBIDDEN"


def test_bootstrap_first_admin_sets_http_only_cookie() -> None:
    revoke_handler = FakeRevokeSessionHandler()
    client = TestClient(create_test_app(revoke_handler=revoke_handler))

    response = client.post(
        "/auth/bootstrap/first-admin",
        json={
            "email": "owner@example.com",
            "display_name": "Owner",
            "team_name": "Hify",
        },
        headers={"Authorization": "Bearer bootstrap-token"},
    )

    assert response.status_code == 201
    assert response.json()["actor"]["role"] == "owner"
    set_cookie = response.headers["set-cookie"]
    assert "hify_session=bootstrap-session-token" in set_cookie
    assert "HttpOnly" in set_cookie


def test_logout_revokes_and_clears_cookie() -> None:
    revoke_handler = FakeRevokeSessionHandler()
    client = TestClient(create_test_app(revoke_handler=revoke_handler))
    client.cookies.set("hify_session", "dev-session-token")

    response = client.post("/auth/logout")

    assert response.status_code == 204
    assert revoke_handler.tokens == ["dev-session-token"]
    assert "hify_session=" in response.headers["set-cookie"]


def test_oidc_login_skeleton_reports_not_implemented() -> None:
    revoke_handler = FakeRevokeSessionHandler()
    client = TestClient(create_test_app(revoke_handler=revoke_handler))

    response = client.get("/auth/oidc/login")

    assert response.status_code == 501
    assert response.json()["detail"]["code"] == "IDENTITY_OIDC_NOT_IMPLEMENTED"


def create_test_app(
    *,
    revoke_handler: FakeRevokeSessionHandler,
    bootstrap_token: str | None = "bootstrap-token",
) -> FastAPI:
    app = FastAPI()
    app.include_router(
        create_auth_router(
            config=AuthRouterConfig(
                cookie_name="hify_session",
                cookie_secure=False,
                cookie_samesite="lax",
                dev_login_enabled=True,
                session_ttl_seconds=3600,
                oidc_enabled=False,
                bootstrap_token=bootstrap_token,
            ),
            bootstrap_first_admin_handler=FakeBootstrapFirstAdminHandler(),
            create_dev_session_handler=FakeCreateDevSessionHandler(),
            revoke_session_handler=revoke_handler,
            request_authenticator=StaticAuthenticator(),
        )
    )
    return app


def create_actor() -> ActorContext:
    return ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="owner",
        permissions=("runs.execute",),
    )
