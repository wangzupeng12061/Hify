from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.runs.application.authorization import require_read_runs
from hify.modules.runs.application.dto import run_diagnostics_info_from_domain
from hify.modules.runs.application.ports import RunsUnitOfWorkFactory
from hify.modules.runs.contracts.dto import RunDiagnosticsInfo
from hify.modules.runs.domain.errors import RunNotFoundError
from hify.modules.usage.contracts.dto import UsageSummaryInfo
from hify.modules.usage.contracts.services import UsageReader
from hify.shared.domain.errors import HifyError


@dataclass(frozen=True, slots=True)
class GetRunDiagnosticsQuery:
    actor: ActorContext
    run_id: UUID


class GetRunDiagnosticsHandler:
    def __init__(
        self,
        unit_of_work_factory: RunsUnitOfWorkFactory,
        usage_reader: UsageReader,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._usage_reader = usage_reader

    async def handle(self, query: GetRunDiagnosticsQuery) -> RunDiagnosticsInfo:
        require_read_runs(query.actor)
        async with self._unit_of_work_factory() as unit_of_work:
            run = await unit_of_work.runs.get_by_id(query.run_id)
            if run is None or run.team_id != query.actor.team_id:
                raise RunNotFoundError("run was not found")
            steps = await unit_of_work.steps.list_by_run(run_id=run.id)
        usage_summary = await self._get_usage_summary(team_id=run.team_id, run_id=run.id)
        return run_diagnostics_info_from_domain(run, steps, usage_summary)

    async def _get_usage_summary(self, *, team_id: UUID, run_id: UUID) -> UsageSummaryInfo:
        try:
            return await self._usage_reader.get_run_summary(team_id=team_id, run_id=run_id)
        except HifyError:
            return UsageSummaryInfo(
                team_id=team_id,
                run_id=run_id,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost_amount=Decimal("0"),
            )
