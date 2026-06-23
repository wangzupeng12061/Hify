from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.usage.application.authorization import require_read_usage
from hify.modules.usage.application.ports import UsageUnitOfWorkFactory
from hify.modules.usage.application.queries.usage_cost_period import resolve_usage_cost_period
from hify.modules.usage.contracts.dto import UsageCostSummaryInfo
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class GetUsageCostSummaryQuery:
    actor: ActorContext
    period_start: datetime | None = None
    period_end: datetime | None = None


class GetUsageCostSummaryHandler:
    def __init__(self, unit_of_work_factory: UsageUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, query: GetUsageCostSummaryQuery) -> UsageCostSummaryInfo:
        require_read_usage(query.actor)
        period_start, period_end = resolve_usage_cost_period(
            period_start=query.period_start,
            period_end=query.period_end,
            clock=self._clock,
        )
        async with self._unit_of_work_factory() as unit_of_work:
            input_tokens, output_tokens, total_tokens, cost_amount = (
                await unit_of_work.records.summarize_for_team_period(
                    team_id=query.actor.team_id,
                    period_start=period_start,
                    period_end=period_end,
                )
            )
            quota = await unit_of_work.quotas.get_by_team(team_id=query.actor.team_id)

        monthly_token_limit = quota.monthly_token_limit if quota is not None else None
        remaining_tokens = (
            None
            if monthly_token_limit is None
            else max(monthly_token_limit - total_tokens, 0)
        )
        return UsageCostSummaryInfo(
            team_id=query.actor.team_id,
            period_start=period_start,
            period_end=period_end,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_amount=Decimal(cost_amount),
            monthly_token_limit=monthly_token_limit,
            remaining_tokens=remaining_tokens,
            is_quota_exceeded=(
                monthly_token_limit is not None and total_tokens >= monthly_token_limit
            ),
        )
