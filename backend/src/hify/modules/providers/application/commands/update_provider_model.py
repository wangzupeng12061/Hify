from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.providers.application.authorization import require_manage_providers
from hify.modules.providers.application.dto import model_info_from_domain
from hify.modules.providers.application.ports import ProvidersUnitOfWorkFactory
from hify.modules.providers.contracts.dto import ModelInfo
from hify.modules.providers.domain.errors import ProviderModelNotFoundError
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class UpdateProviderModelCommand:
    actor: ActorContext
    model_id: UUID
    display_name: str
    context_window_tokens: int
    supports_tools: bool
    supports_vision: bool
    supports_structured_output: bool


class UpdateProviderModelHandler:
    def __init__(self, unit_of_work_factory: ProvidersUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: UpdateProviderModelCommand) -> ModelInfo:
        require_manage_providers(command.actor)
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            model = await unit_of_work.models.get_by_id(command.model_id)
            if model is None or model.team_id != command.actor.team_id:
                raise ProviderModelNotFoundError("provider model was not found")

            provider = await unit_of_work.providers.get_by_id(model.provider_id)
            if provider is None or provider.team_id != command.actor.team_id:
                raise ProviderModelNotFoundError("provider model was not found")

            model.update_configuration(
                display_name=command.display_name,
                context_window_tokens=command.context_window_tokens,
                supports_tools=command.supports_tools,
                supports_vision=command.supports_vision,
                supports_structured_output=command.supports_structured_output,
                now=now,
            )
            await unit_of_work.models.save(model)
            await unit_of_work.commit()

        return model_info_from_domain(provider, model)
