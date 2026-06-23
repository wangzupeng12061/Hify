from __future__ import annotations

from dataclasses import dataclass

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.usage.application.authorization import require_manage_usage
from hify.modules.usage.application.dto import usage_quota_info_from_domain
from hify.modules.usage.application.ports import UsageUnitOfWorkFactory
from hify.modules.usage.contracts.dto import UsageQuotaInfo
from hify.modules.usage.domain.entities import UsageQuota
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class SetTeamUsageQuotaCommand:
    actor: ActorContext
    monthly_token_limit: int | None


class SetTeamUsageQuotaHandler:
    def __init__(self, unit_of_work_factory: UsageUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: SetTeamUsageQuotaCommand) -> UsageQuotaInfo:
        require_manage_usage(command.actor)
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            quota = await unit_of_work.quotas.get_by_team(team_id=command.actor.team_id)
            if quota is None:
                quota = UsageQuota.create(
                    team_id=command.actor.team_id,
                    monthly_token_limit=command.monthly_token_limit,
                    created_by=command.actor.user_id,
                    now=now,
                )
                await unit_of_work.quotas.add(quota)
            else:
                quota.update_monthly_token_limit(
                    monthly_token_limit=command.monthly_token_limit,
                    updated_by=command.actor.user_id,
                    now=now,
                )
                await unit_of_work.quotas.save(quota)
            await unit_of_work.commit()
        return usage_quota_info_from_domain(quota)
