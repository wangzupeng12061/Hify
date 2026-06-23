from __future__ import annotations

from dataclasses import dataclass

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.providers.application.authorization import require_manage_providers
from hify.modules.providers.application.dto import model_info_from_domain
from hify.modules.providers.application.ports import ProvidersUnitOfWorkFactory
from hify.modules.providers.contracts.dto import ModelInfo


@dataclass(frozen=True, slots=True)
class ListModelsForActorQuery:
    actor: ActorContext


class ListModelsForActorHandler:
    def __init__(self, unit_of_work_factory: ProvidersUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: ListModelsForActorQuery) -> tuple[ModelInfo, ...]:
        require_manage_providers(query.actor)
        async with self._unit_of_work_factory() as unit_of_work:
            models = await unit_of_work.models.list_by_team(query.actor.team_id)
            provider_ids = frozenset(model.provider_id for model in models)
            providers = await unit_of_work.providers.list_by_ids(provider_ids)

        return tuple(
            model_info_from_domain(provider, model)
            for model in models
            if (provider := providers.get(model.provider_id)) is not None
        )
