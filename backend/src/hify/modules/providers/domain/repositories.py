from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.providers.domain.entities import ModelProvider, ProviderCredential, ProviderModel
from hify.modules.providers.domain.value_objects import ProviderType


class ModelProviderRepository(Protocol):
    async def add(self, provider: ModelProvider) -> None: ...

    async def get_by_id(self, provider_id: UUID) -> ModelProvider | None: ...

    async def list_by_ids(self, provider_ids: frozenset[UUID]) -> dict[UUID, ModelProvider]: ...

    async def get_by_team_type_and_name(
        self,
        *,
        team_id: UUID,
        provider_type: ProviderType,
        name: str,
    ) -> ModelProvider | None: ...


class ProviderCredentialRepository(Protocol):
    async def add(self, credential: ProviderCredential) -> None: ...

    async def get_by_provider_id(self, provider_id: UUID) -> ProviderCredential | None: ...


class ProviderModelRepository(Protocol):
    async def add(self, model: ProviderModel) -> None: ...

    async def get_by_id(self, model_id: UUID) -> ProviderModel | None: ...

    async def get_by_provider_and_name(
        self,
        *,
        provider_id: UUID,
        model_name: str,
    ) -> ProviderModel | None: ...

    async def list_by_team(self, team_id: UUID) -> tuple[ProviderModel, ...]: ...
