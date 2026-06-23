from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.providers.application.authorization import require_manage_providers
from hify.modules.providers.application.dto import model_info_from_domain
from hify.modules.providers.application.ports import ProvidersUnitOfWorkFactory
from hify.modules.providers.contracts.dto import ModelInfo
from hify.modules.providers.domain.errors import ProviderModelNotFoundError
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class SetProviderModelPricingCommand:
    actor: ActorContext
    model_id: UUID
    price_per_1m_input_tokens: Decimal | None
    price_per_1m_output_tokens: Decimal | None


class SetProviderModelPricingHandler:
    def __init__(self, unit_of_work_factory: ProvidersUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: SetProviderModelPricingCommand) -> ModelInfo:
        require_manage_providers(command.actor)
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            model = await unit_of_work.models.get_by_id(command.model_id)
            if model is None or model.team_id != command.actor.team_id:
                raise ProviderModelNotFoundError("provider model was not found")

            provider = await unit_of_work.providers.get_by_id(model.provider_id)
            if provider is None or provider.team_id != command.actor.team_id:
                raise ProviderModelNotFoundError("provider model was not found")

            model.set_pricing(
                price_per_1m_input_tokens=command.price_per_1m_input_tokens,
                price_per_1m_output_tokens=command.price_per_1m_output_tokens,
                now=now,
            )
            await unit_of_work.models.save(model)
            await unit_of_work.commit()

        return model_info_from_domain(provider, model)
