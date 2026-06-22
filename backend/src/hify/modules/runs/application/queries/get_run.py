from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.runs.application.authorization import require_read_runs
from hify.modules.runs.application.dto import run_info_from_domain
from hify.modules.runs.application.ports import RunsUnitOfWorkFactory
from hify.modules.runs.contracts.dto import RunInfo
from hify.modules.runs.domain.errors import RunNotFoundError


@dataclass(frozen=True, slots=True)
class GetRunQuery:
    team_id: UUID
    run_id: UUID


@dataclass(frozen=True, slots=True)
class GetRunForActorQuery:
    actor: ActorContext
    run_id: UUID


class GetRunHandler:
    def __init__(self, unit_of_work_factory: RunsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetRunQuery) -> RunInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            run = await unit_of_work.runs.get_by_id(query.run_id)
        if run is None or run.team_id != query.team_id:
            raise RunNotFoundError("run was not found")
        return run_info_from_domain(run)


class GetRunForActorHandler:
    def __init__(self, get_run_handler: GetRunHandler) -> None:
        self._get_run_handler = get_run_handler

    async def handle(self, query: GetRunForActorQuery) -> RunInfo:
        require_read_runs(query.actor)
        return await self._get_run_handler.handle(
            GetRunQuery(team_id=query.actor.team_id, run_id=query.run_id)
        )
