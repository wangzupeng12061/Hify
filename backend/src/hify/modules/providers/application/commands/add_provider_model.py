from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.providers.application.authorization import require_manage_providers
from hify.modules.providers.application.dto import model_info_from_domain
from hify.modules.providers.application.ports import ProvidersUnitOfWorkFactory
from hify.modules.providers.contracts.dto import ModelInfo
from hify.modules.providers.domain.entities import ProviderModel
from hify.modules.providers.domain.errors import (
    ProviderModelAlreadyExistsError,
    ProviderNotFoundError,
)
from hify.modules.providers.domain.value_objects import normalize_model_name, parse_model_kind
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class AddProviderModelCommand:
    actor: ActorContext
    provider_id: UUID
    model_name: str
    display_name: str
    kind: str
    context_window_tokens: int
    supports_tools: bool
    supports_vision: bool
    supports_structured_output: bool


class AddProviderModelHandler:
    def __init__(self, unit_of_work_factory: ProvidersUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: AddProviderModelCommand) -> ModelInfo:
        require_manage_providers(command.actor)
        model_name = normalize_model_name(command.model_name)
        kind = parse_model_kind(command.kind)
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            provider = await unit_of_work.providers.get_by_id(command.provider_id)
            if provider is None or provider.team_id != command.actor.team_id:
                raise ProviderNotFoundError("provider was not found")

            existing_model = await unit_of_work.models.get_by_provider_and_name(
                provider_id=command.provider_id,
                model_name=model_name,
            )
            if existing_model is not None:
                raise ProviderModelAlreadyExistsError("provider model already exists")

            model = ProviderModel.create(
                team_id=command.actor.team_id,
                provider_id=provider.id,
                model_name=model_name,
                display_name=command.display_name,
                kind=kind,
                context_window_tokens=command.context_window_tokens,
                supports_tools=command.supports_tools,
                supports_vision=command.supports_vision,
                supports_structured_output=command.supports_structured_output,
                now=now,
            )
            await unit_of_work.models.add(model)
            await unit_of_work.commit()

        return model_info_from_domain(provider, model)
