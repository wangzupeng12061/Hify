from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.usage.application.authorization import require_read_usage
from hify.modules.usage.application.ports import UsageUnitOfWorkFactory
from hify.modules.usage.contracts.dto import UsageSummaryInfo


@dataclass(frozen=True, slots=True)
class GetRunUsageSummaryQuery:
    actor: ActorContext
    run_id: UUID


class GetRunUsageSummaryHandler:
    def __init__(self, unit_of_work_factory: UsageUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetRunUsageSummaryQuery) -> UsageSummaryInfo:
        require_read_usage(query.actor)
        async with self._unit_of_work_factory() as unit_of_work:
            input_tokens, output_tokens, total_tokens, cost_amount = (
                await unit_of_work.records.summarize_for_run(
                    team_id=query.actor.team_id,
                    run_id=query.run_id,
                )
            )
        return UsageSummaryInfo(
            team_id=query.actor.team_id,
            run_id=query.run_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_amount=Decimal(cost_amount),
        )
