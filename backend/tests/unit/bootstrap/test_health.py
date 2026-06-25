from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi import APIRouter
from fastapi.testclient import TestClient

from hify.bootstrap.api import create_app
from hify.bootstrap.settings import Settings


class FakeConnection:
    async def __aenter__(self) -> FakeConnection:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        return None

    async def execute(self, statement: object) -> None:
        return None


class FakeEngine:
    def connect(self) -> FakeConnection:
        return FakeConnection()


class BrokenEngine:
    def connect(self) -> FakeConnection:
        raise RuntimeError("database unavailable")


def test_health_live_returns_ok() -> None:
    client = TestClient(create_app(_container(Settings(redis_url=""))))

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_requires_database_and_provider_credential_key() -> None:
    client = TestClient(
        create_app(
            _container(
                Settings(
                    provider_credential_encryption_key="",
                    redis_url="",
                )
            )
        )
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "ok"
    assert response.json()["checks"]["provider_credential_encryption_key"] == "missing"


def test_health_ready_fails_when_database_is_unavailable() -> None:
    client = TestClient(
        create_app(
            _container(
                Settings(
                    provider_credential_encryption_key="configured",
                    redis_url="",
                ),
                engine=BrokenEngine(),
            )
        )
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "unavailable"


def test_health_ready_rejects_development_login_in_production() -> None:
    client = TestClient(
        create_app(
            _container(
                Settings(
                    deployment_mode="production",
                    provider_credential_encryption_key="configured",
                    auth_dev_login_enabled=True,
                    redis_url="",
                )
            )
        )
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["auth"] == "development_login_enabled"


def test_health_ready_rejects_unimplemented_oidc_only_in_production() -> None:
    client = TestClient(
        create_app(
            _container(
                Settings(
                    deployment_mode="production",
                    provider_credential_encryption_key="configured",
                    auth_oidc_enabled=True,
                    redis_url="",
                )
            )
        )
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["auth"] == "oidc_not_implemented"


def test_health_ready_accepts_trusted_header_auth_in_production() -> None:
    client = TestClient(
        create_app(
            _container(
                Settings(
                    deployment_mode="production",
                    provider_credential_encryption_key="configured",
                    auth_trusted_header_enabled=True,
                    redis_url="",
                )
            )
        )
    )

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["checks"]["auth"] == "ok"


def _container(settings: Settings, *, engine: object | None = None) -> Any:
    return SimpleNamespace(
        settings=settings,
        engine=engine or FakeEngine(),
        identity=_module(),
        providers=_module(),
        agents=_module(),
        conversations=_module(),
        jobs=_module(),
        knowledge=_module(),
        mcp=_module(),
        runs=_module(),
        tools=_module(),
        usage=_module(),
        workflows=_module(),
    )


def _module() -> SimpleNamespace:
    return SimpleNamespace(router=APIRouter())
