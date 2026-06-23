from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.providers.domain.entities import ModelProvider, ProviderCredential, ProviderModel
from hify.modules.providers.domain.value_objects import (
    CredentialSecret,
    CredentialStatus,
    ModelKind,
    ModelStatus,
    ProviderStatus,
    ProviderType,
)
from hify.modules.providers.infrastructure.database.models import (
    ModelProviderModel,
    ProviderCredentialModel,
    ProviderModelModel,
)


class SqlAlchemyModelProviderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, provider: ModelProvider) -> None:
        self._session.add(_provider_to_model(provider))

    async def get_by_id(self, provider_id: UUID) -> ModelProvider | None:
        model = await self._session.get(ModelProviderModel, provider_id)
        if model is None:
            return None
        return _provider_from_model(model)

    async def list_by_ids(self, provider_ids: frozenset[UUID]) -> dict[UUID, ModelProvider]:
        if not provider_ids:
            return {}
        statement = select(ModelProviderModel).where(ModelProviderModel.id.in_(provider_ids))
        models = await self._session.scalars(statement)
        providers = (_provider_from_model(model) for model in models)
        return {provider.id: provider for provider in providers}

    async def get_by_team_type_and_name(
        self,
        *,
        team_id: UUID,
        provider_type: ProviderType,
        name: str,
    ) -> ModelProvider | None:
        statement = select(ModelProviderModel).where(
            ModelProviderModel.team_id == team_id,
            ModelProviderModel.provider_type == provider_type.value,
            func.lower(ModelProviderModel.name) == name.lower(),
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _provider_from_model(model)


class SqlAlchemyProviderCredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, credential: ProviderCredential) -> None:
        self._session.add(_credential_to_model(credential))

    async def get_by_provider_id(self, provider_id: UUID) -> ProviderCredential | None:
        statement = select(ProviderCredentialModel).where(
            ProviderCredentialModel.provider_id == provider_id
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _credential_from_model(model)


class SqlAlchemyProviderModelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, model: ProviderModel) -> None:
        self._session.add(_model_to_model(model))

    async def save(self, model: ProviderModel) -> None:
        existing_model = await self._session.get(ProviderModelModel, model.id)
        if existing_model is None:
            self._session.add(_model_to_model(model))
            return
        existing_model.model_name = model.model_name
        existing_model.display_name = model.display_name
        existing_model.kind = model.kind.value
        existing_model.status = model.status.value
        existing_model.context_window_tokens = model.context_window_tokens
        existing_model.supports_tools = model.supports_tools
        existing_model.supports_vision = model.supports_vision
        existing_model.supports_structured_output = model.supports_structured_output
        existing_model.price_per_1m_input_tokens = model.price_per_1m_input_tokens
        existing_model.price_per_1m_output_tokens = model.price_per_1m_output_tokens
        existing_model.version = model.version
        existing_model.updated_at = model.updated_at

    async def get_by_id(self, model_id: UUID) -> ProviderModel | None:
        model = await self._session.get(ProviderModelModel, model_id)
        if model is None:
            return None
        return _model_from_model(model)

    async def get_by_provider_and_name(
        self,
        *,
        provider_id: UUID,
        model_name: str,
    ) -> ProviderModel | None:
        statement = select(ProviderModelModel).where(
            ProviderModelModel.provider_id == provider_id,
            func.lower(ProviderModelModel.model_name) == model_name.lower(),
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _model_from_model(model)

    async def list_by_team(self, team_id: UUID) -> tuple[ProviderModel, ...]:
        statement = (
            select(ProviderModelModel)
            .where(ProviderModelModel.team_id == team_id)
            .order_by(ProviderModelModel.created_at.desc(), ProviderModelModel.id.desc())
        )
        models = await self._session.scalars(statement)
        return tuple(_model_from_model(model) for model in models)


def _provider_to_model(provider: ModelProvider) -> ModelProviderModel:
    return ModelProviderModel(
        id=provider.id,
        team_id=provider.team_id,
        provider_type=provider.provider_type.value,
        name=provider.name,
        base_url=provider.base_url,
        status=provider.status.value,
        version=provider.version,
        created_by=provider.created_by,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


def _provider_from_model(model: ModelProviderModel) -> ModelProvider:
    return ModelProvider(
        id=model.id,
        team_id=model.team_id,
        provider_type=ProviderType(model.provider_type),
        name=model.name,
        base_url=model.base_url,
        status=ProviderStatus(model.status),
        version=model.version,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _credential_to_model(credential: ProviderCredential) -> ProviderCredentialModel:
    return ProviderCredentialModel(
        id=credential.id,
        team_id=credential.team_id,
        provider_id=credential.provider_id,
        secret_ciphertext=credential.secret.ciphertext,
        key_version=credential.secret.key_version,
        secret_fingerprint=credential.secret.fingerprint,
        status=credential.status.value,
        version=credential.version,
        created_at=credential.created_at,
        updated_at=credential.updated_at,
    )


def _credential_from_model(model: ProviderCredentialModel) -> ProviderCredential:
    return ProviderCredential(
        id=model.id,
        team_id=model.team_id,
        provider_id=model.provider_id,
        secret=CredentialSecret(
            ciphertext=model.secret_ciphertext,
            key_version=model.key_version,
            fingerprint=model.secret_fingerprint,
        ),
        status=CredentialStatus(model.status),
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _model_to_model(model: ProviderModel) -> ProviderModelModel:
    return ProviderModelModel(
        id=model.id,
        team_id=model.team_id,
        provider_id=model.provider_id,
        model_name=model.model_name,
        display_name=model.display_name,
        kind=model.kind.value,
        status=model.status.value,
        context_window_tokens=model.context_window_tokens,
        supports_tools=model.supports_tools,
        supports_vision=model.supports_vision,
        supports_structured_output=model.supports_structured_output,
        price_per_1m_input_tokens=model.price_per_1m_input_tokens,
        price_per_1m_output_tokens=model.price_per_1m_output_tokens,
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _model_from_model(model: ProviderModelModel) -> ProviderModel:
    return ProviderModel(
        id=model.id,
        team_id=model.team_id,
        provider_id=model.provider_id,
        model_name=model.model_name,
        display_name=model.display_name,
        kind=ModelKind(model.kind),
        status=ModelStatus(model.status),
        context_window_tokens=model.context_window_tokens,
        supports_tools=model.supports_tools,
        supports_vision=model.supports_vision,
        supports_structured_output=model.supports_structured_output,
        price_per_1m_input_tokens=model.price_per_1m_input_tokens,
        price_per_1m_output_tokens=model.price_per_1m_output_tokens,
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
