from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.providers.application.dto import model_info_from_domain
from hify.modules.providers.application.ports import ProvidersUnitOfWorkFactory
from hify.modules.providers.contracts.dto import ModelInfo, ModelPricingInfo
from hify.modules.providers.contracts.services import ModelCatalog, ModelPricingCatalog
from hify.modules.providers.domain.errors import ProviderModelNotFoundError


@dataclass(frozen=True, slots=True)
class GetModelQuery:
    team_id: UUID
    model_id: UUID


class GetModelHandler:
    def __init__(self, unit_of_work_factory: ProvidersUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetModelQuery) -> ModelInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            model = await unit_of_work.models.get_by_id(query.model_id)
            if model is None or model.team_id != query.team_id:
                raise ProviderModelNotFoundError("provider model was not found")
            provider = await unit_of_work.providers.get_by_id(model.provider_id)
            if provider is None or provider.team_id != query.team_id:
                raise ProviderModelNotFoundError("provider model was not found")

        return model_info_from_domain(provider, model)


class ListModelsHandler:
    def __init__(self, unit_of_work_factory: ProvidersUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, *, team_id: UUID) -> tuple[ModelInfo, ...]:
        async with self._unit_of_work_factory() as unit_of_work:
            models = await unit_of_work.models.list_by_team(team_id)
            provider_ids = frozenset(model.provider_id for model in models)
            providers = await unit_of_work.providers.list_by_ids(provider_ids)

        return tuple(
            model_info_from_domain(provider, model)
            for model in models
            if (provider := providers[model.provider_id]) is not None
        )


@dataclass(frozen=True, slots=True)
class GetModelPricingQuery:
    team_id: UUID
    model_id: UUID


class GetModelPricingHandler:
    def __init__(self, unit_of_work_factory: ProvidersUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetModelPricingQuery) -> ModelPricingInfo | None:
        async with self._unit_of_work_factory() as unit_of_work:
            model = await unit_of_work.models.get_by_id(query.model_id)
            if model is None or model.team_id != query.team_id:
                return None

        return ModelPricingInfo(
            provider_model_id=model.id,
            team_id=model.team_id,
            price_per_1m_input_tokens=model.price_per_1m_input_tokens,
            price_per_1m_output_tokens=model.price_per_1m_output_tokens,
        )


class ModelCatalogService(ModelCatalog):
    def __init__(
        self,
        get_model_handler: GetModelHandler,
        list_models_handler: ListModelsHandler,
    ) -> None:
        self._get_model_handler = get_model_handler
        self._list_models_handler = list_models_handler

    async def get_model(self, *, team_id: UUID, model_id: UUID) -> ModelInfo:
        return await self._get_model_handler.handle(GetModelQuery(team_id=team_id, model_id=model_id))

    async def list_models(self, *, team_id: UUID) -> tuple[ModelInfo, ...]:
        return await self._list_models_handler.handle(team_id=team_id)


class ModelPricingCatalogService(ModelPricingCatalog):
    def __init__(self, get_model_pricing_handler: GetModelPricingHandler) -> None:
        self._get_model_pricing_handler = get_model_pricing_handler

    async def get_model_pricing(
        self,
        *,
        team_id: UUID,
        model_id: UUID,
    ) -> ModelPricingInfo | None:
        return await self._get_model_pricing_handler.handle(
            GetModelPricingQuery(team_id=team_id, model_id=model_id)
        )
