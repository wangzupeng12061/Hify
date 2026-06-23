from __future__ import annotations

from datetime import datetime
from uuid import UUID

from hify.modules.usage.application.ports import UsageUnitOfWorkFactory
from hify.modules.usage.application.quota_period import month_period_for
from hify.modules.usage.contracts.dto import UsageQuotaStatusInfo
from hify.modules.usage.contracts.errors import UsageQuotaExceededError
from hify.modules.usage.contracts.services import UsageQuotaChecker


class UsageQuotaCheckerService(UsageQuotaChecker):
    def __init__(self, unit_of_work_factory: UsageUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def ensure_team_quota_available(
        self,
        *,
        team_id: UUID,
        at: datetime,
    ) -> UsageQuotaStatusInfo:
        period_start, period_end = month_period_for(at)
        async with self._unit_of_work_factory() as unit_of_work:
            quota = await unit_of_work.quotas.get_by_team(team_id=team_id)
            _, _, used_tokens, _ = await unit_of_work.records.summarize_for_team_period(
                team_id=team_id,
                period_start=period_start,
                period_end=period_end,
            )

        monthly_token_limit = quota.monthly_token_limit if quota is not None else None
        remaining_tokens = (
            max(monthly_token_limit - used_tokens, 0)
            if monthly_token_limit is not None
            else None
        )
        status = UsageQuotaStatusInfo(
            team_id=team_id,
            monthly_token_limit=monthly_token_limit,
            used_tokens=used_tokens,
            remaining_tokens=remaining_tokens,
            is_exceeded=monthly_token_limit is not None and used_tokens >= monthly_token_limit,
            period_start=period_start,
            period_end=period_end,
        )
        if status.is_exceeded:
            raise UsageQuotaExceededError(
                "team monthly token quota has been exceeded",
                metadata={
                    "team_id": str(team_id),
                    "monthly_token_limit": monthly_token_limit,
                    "used_tokens": used_tokens,
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                },
            )
        return status
