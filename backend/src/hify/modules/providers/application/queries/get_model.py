from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.providers.application.dto import model_info_from_domain
from hify.modules.providers.application.ports import ProvidersUnitOfWorkFactory
from hify.modules.providers.contracts.dto import ModelInfo
from hify.modules.providers.contracts.services import ModelCatalog
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
            providers = {
                model.provider_id: await unit_of_work.providers.get_by_id(model.provider_id)
                for model in models
            }

        return tuple(
            model_info_from_domain(provider, model)
            for model in models
            if (provider := providers[model.provider_id]) is not None
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
