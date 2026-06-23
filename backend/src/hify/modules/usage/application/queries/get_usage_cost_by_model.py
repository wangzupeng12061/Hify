from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.usage.application.authorization import require_read_usage
from hify.modules.usage.application.ports import UsageUnitOfWorkFactory
from hify.modules.usage.application.queries.usage_cost_period import resolve_usage_cost_period
from hify.modules.usage.contracts.dto import UsageCostByModelInfo, UsageCostByModelItemInfo
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class GetUsageCostByModelQuery:
    actor: ActorContext
    period_start: datetime | None = None
    period_end: datetime | None = None


class GetUsageCostByModelHandler:
    def __init__(self, unit_of_work_factory: UsageUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, query: GetUsageCostByModelQuery) -> UsageCostByModelInfo:
        require_read_usage(query.actor)
        period_start, period_end = resolve_usage_cost_period(
            period_start=query.period_start,
            period_end=query.period_end,
            clock=self._clock,
        )
        async with self._unit_of_work_factory() as unit_of_work:
            rows = await unit_of_work.records.summarize_by_model_for_team_period(
                team_id=query.actor.team_id,
                period_start=period_start,
                period_end=period_end,
            )
        return UsageCostByModelInfo(
            team_id=query.actor.team_id,
            period_start=period_start,
            period_end=period_end,
            items=tuple(
                UsageCostByModelItemInfo(
                    provider_model_id=provider_model_id,
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost_amount=Decimal(cost_amount),
                )
                for (
                    provider_model_id,
                    provider,
                    model,
                    input_tokens,
                    output_tokens,
                    total_tokens,
                    cost_amount,
                ) in rows
            ),
        )
