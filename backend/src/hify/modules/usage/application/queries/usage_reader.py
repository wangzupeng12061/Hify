from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from hify.modules.usage.application.ports import UsageUnitOfWorkFactory
from hify.modules.usage.contracts.dto import UsageSummaryInfo
from hify.modules.usage.contracts.services import UsageReader


class UsageReaderService(UsageReader):
    def __init__(self, unit_of_work_factory: UsageUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def get_team_summary(self, *, team_id: UUID) -> UsageSummaryInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            input_tokens, output_tokens, total_tokens, cost_amount = (
                await unit_of_work.records.summarize_for_team(team_id=team_id)
            )
        return UsageSummaryInfo(
            team_id=team_id,
            run_id=None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_amount=Decimal(cost_amount),
        )

    async def get_run_summary(self, *, team_id: UUID, run_id: UUID) -> UsageSummaryInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            input_tokens, output_tokens, total_tokens, cost_amount = (
                await unit_of_work.records.summarize_for_run(team_id=team_id, run_id=run_id)
            )
        return UsageSummaryInfo(
            team_id=team_id,
            run_id=run_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_amount=Decimal(cost_amount),
        )
