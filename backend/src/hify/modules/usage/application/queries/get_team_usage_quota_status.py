from __future__ import annotations

from dataclasses import dataclass

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.usage.application.authorization import require_read_usage
from hify.modules.usage.application.ports import UsageUnitOfWorkFactory
from hify.modules.usage.application.quota_period import month_period_for
from hify.modules.usage.contracts.dto import UsageQuotaStatusInfo
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class GetTeamUsageQuotaStatusQuery:
    actor: ActorContext


class GetTeamUsageQuotaStatusHandler:
    def __init__(self, unit_of_work_factory: UsageUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, query: GetTeamUsageQuotaStatusQuery) -> UsageQuotaStatusInfo:
        require_read_usage(query.actor)
        period_start, period_end = month_period_for(self._clock.now())
        async with self._unit_of_work_factory() as unit_of_work:
            quota = await unit_of_work.quotas.get_by_team(team_id=query.actor.team_id)
            _, _, used_tokens, _ = await unit_of_work.records.summarize_for_team_period(
                team_id=query.actor.team_id,
                period_start=period_start,
                period_end=period_end,
            )
        monthly_token_limit = quota.monthly_token_limit if quota is not None else None
        remaining_tokens = (
            max(monthly_token_limit - used_tokens, 0)
            if monthly_token_limit is not None
            else None
        )
        return UsageQuotaStatusInfo(
            team_id=query.actor.team_id,
            monthly_token_limit=monthly_token_limit,
            used_tokens=used_tokens,
            remaining_tokens=remaining_tokens,
            is_exceeded=monthly_token_limit is not None and used_tokens >= monthly_token_limit,
            period_start=period_start,
            period_end=period_end,
        )
