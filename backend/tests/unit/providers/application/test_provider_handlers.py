from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.providers.application.commands.add_provider_model import (
    AddProviderModelCommand,
    AddProviderModelHandler,
)
from hify.modules.providers.application.commands.create_provider import (
    CreateProviderCommand,
    CreateProviderHandler,
)
from hify.modules.providers.application.queries.get_model import (
    GetModelHandler,
    ListModelsHandler,
    ModelCatalogService,
)
from hify.modules.providers.domain.entities import ModelProvider, ProviderCredential, ProviderModel
from hify.modules.providers.domain.errors import (
    ProviderAlreadyExistsError,
    ProviderModelAlreadyExistsError,
    ProviderPermissionDeniedError,
)
from hify.modules.providers.domain.value_objects import CredentialSecret, ProviderType
from hify.shared.domain.clock import Clock


class FixedClock(Clock):
    def now(self) -> datetime:
        return datetime(2026, 6, 22, tzinfo=UTC)


class FakeCredentialEncryptor:
    def encrypt(self, plaintext: str) -> CredentialSecret:
        return CredentialSecret(
            ciphertext=f"encrypted:{plaintext}".encode(),
            key_version=1,
            fingerprint="fingerprint",
        )


class FakeProviderRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, ModelProvider] = {}

    async def add(self, provider: ModelProvider) -> None:
        self.items[provider.id] = provider

    async def get_by_id(self, provider_id: UUID) -> ModelProvider | None:
        return self.items.get(provider_id)

    async def list_by_ids(self, provider_ids: frozenset[UUID]) -> dict[UUID, ModelProvider]:
        return {
            provider_id: provider
            for provider_id, provider in self.items.items()
            if provider_id in provider_ids
        }

    async def get_by_team_type_and_name(
        self,
        *,
        team_id: UUID,
        provider_type: ProviderType,
        name: str,
    ) -> ModelProvider | None:
        for provider in self.items.values():
            if (
                provider.team_id == team_id
                and provider.provider_type == provider_type
                and provider.name.lower() == name.lower()
            ):
                return provider
        return None


class FakeCredentialRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, ProviderCredential] = {}

    async def add(self, credential: ProviderCredential) -> None:
        self.items[credential.id] = credential

    async def get_by_provider_id(self, provider_id: UUID) -> ProviderCredential | None:
        for credential in self.items.values():
            if credential.provider_id == provider_id:
                return credential
        return None


class FakeModelRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, ProviderModel] = {}

    async def add(self, model: ProviderModel) -> None:
        self.items[model.id] = model

    async def get_by_id(self, model_id: UUID) -> ProviderModel | None:
        return self.items.get(model_id)

    async def get_by_provider_and_name(
        self,
        *,
        provider_id: UUID,
        model_name: str,
    ) -> ProviderModel | None:
        for model in self.items.values():
            if model.provider_id == provider_id and model.model_name.lower() == model_name.lower():
                return model
        return None

    async def list_by_team(self, team_id: UUID) -> tuple[ProviderModel, ...]:
        return tuple(model for model in self.items.values() if model.team_id == team_id)


class FakeProvidersUnitOfWork:
    def __init__(self) -> None:
        self.providers = FakeProviderRepository()
        self.credentials = FakeCredentialRepository()
        self.models = FakeModelRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def actor_with_provider_permission() -> ActorContext:
    return ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="admin",
        permissions=("providers.manage",),
    )


@pytest.mark.asyncio
async def test_create_provider_encrypts_credential_and_rejects_duplicate() -> None:
    unit_of_work = FakeProvidersUnitOfWork()
    handler = CreateProviderHandler(lambda: unit_of_work, FakeCredentialEncryptor(), FixedClock())
    command = CreateProviderCommand(
        actor=actor_with_provider_permission(),
        provider_type="openai",
        name="OpenAI",
        base_url=None,
        credential_plaintext="secret",
    )

    provider = await handler.handle(command)

    credential = await unit_of_work.credentials.get_by_provider_id(provider.id)
    assert credential is not None
    assert credential.secret.ciphertext == b"encrypted:secret"
    with pytest.raises(ProviderAlreadyExistsError):
        await handler.handle(command)


@pytest.mark.asyncio
async def test_create_provider_requires_permission() -> None:
    unit_of_work = FakeProvidersUnitOfWork()
    handler = CreateProviderHandler(lambda: unit_of_work, FakeCredentialEncryptor(), FixedClock())
    actor = ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="viewer",
        permissions=(),
    )

    with pytest.raises(ProviderPermissionDeniedError):
        await handler.handle(
            CreateProviderCommand(
                actor=actor,
                provider_type="openai",
                name="OpenAI",
                base_url=None,
                credential_plaintext="secret",
            )
        )


@pytest.mark.asyncio
async def test_add_provider_model_and_catalog_queries() -> None:
    unit_of_work = FakeProvidersUnitOfWork()
    actor = actor_with_provider_permission()
    provider = await CreateProviderHandler(
        lambda: unit_of_work,
        FakeCredentialEncryptor(),
        FixedClock(),
    ).handle(
        CreateProviderCommand(
            actor=actor,
            provider_type="openai",
            name="OpenAI",
            base_url=None,
            credential_plaintext="secret",
        )
    )
    handler = AddProviderModelHandler(lambda: unit_of_work, FixedClock())

    model = await handler.handle(
        AddProviderModelCommand(
            actor=actor,
            provider_id=provider.id,
            model_name="gpt-4.1",
            display_name="GPT 4.1",
            kind="chat",
            context_window_tokens=128000,
            supports_tools=True,
            supports_vision=True,
            supports_structured_output=True,
        )
    )

    catalog = ModelCatalogService(GetModelHandler(lambda: unit_of_work), ListModelsHandler(lambda: unit_of_work))
    fetched = await catalog.get_model(team_id=actor.team_id, model_id=model.id)
    listed = await catalog.list_models(team_id=actor.team_id)
    assert fetched.model_name == "gpt-4.1"
    assert listed == (fetched,)


@pytest.mark.asyncio
async def test_add_provider_model_rejects_duplicate_name_case_insensitive() -> None:
    unit_of_work = FakeProvidersUnitOfWork()
    actor = actor_with_provider_permission()
    provider = await CreateProviderHandler(
        lambda: unit_of_work,
        FakeCredentialEncryptor(),
        FixedClock(),
    ).handle(
        CreateProviderCommand(
            actor=actor,
            provider_type="openai",
            name="OpenAI",
            base_url=None,
            credential_plaintext="secret",
        )
    )
    handler = AddProviderModelHandler(lambda: unit_of_work, FixedClock())
    command = AddProviderModelCommand(
        actor=actor,
        provider_id=provider.id,
        model_name="gpt-4.1",
        display_name="GPT 4.1",
        kind="chat",
        context_window_tokens=128000,
        supports_tools=True,
        supports_vision=False,
        supports_structured_output=True,
    )

    await handler.handle(command)
    duplicate_command = AddProviderModelCommand(
        actor=actor,
        provider_id=provider.id,
        model_name="GPT-4.1",
        display_name="GPT 4.1",
        kind="chat",
        context_window_tokens=128000,
        supports_tools=True,
        supports_vision=False,
        supports_structured_output=True,
    )

    with pytest.raises(ProviderModelAlreadyExistsError):
        await handler.handle(duplicate_command)
