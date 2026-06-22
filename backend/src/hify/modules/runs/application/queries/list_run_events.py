from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.runs.application.authorization import require_read_runs
from hify.modules.runs.application.dto import run_event_info_from_domain
from hify.modules.runs.application.ports import RunsUnitOfWorkFactory
from hify.modules.runs.application.queries.get_run import GetRunHandler, GetRunQuery
from hify.modules.runs.contracts.dto import RunEventPage, RunInfo
from hify.modules.runs.contracts.services import RunReader
from hify.modules.runs.domain.errors import RunNotFoundError
from hify.modules.runs.domain.value_objects import parse_event_cursor
from hify.shared.domain.pagination import PageRequest, build_page


@dataclass(frozen=True, slots=True)
class ListRunEventsQuery:
    team_id: UUID
    run_id: UUID
    cursor: str | None
    limit: int


@dataclass(frozen=True, slots=True)
class ListRunEventsForActorQuery:
    actor: ActorContext
    run_id: UUID
    cursor: str | None
    limit: int


class ListRunEventsHandler:
    def __init__(self, unit_of_work_factory: RunsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: ListRunEventsQuery) -> RunEventPage:
        page_request = PageRequest(limit=query.limit, cursor=query.cursor)
        after_sequence_number = parse_event_cursor(query.cursor)

        async with self._unit_of_work_factory() as unit_of_work:
            run = await unit_of_work.runs.get_by_id(query.run_id)
            if run is None or run.team_id != query.team_id:
                raise RunNotFoundError("run was not found")
            events = await unit_of_work.events.list_by_run(
                run_id=query.run_id,
                after_sequence_number=after_sequence_number,
                limit=page_request.limit_plus_one,
            )

        next_cursor = (
            str(events[page_request.limit - 1].sequence_number)
            if len(events) > page_request.limit
            else None
        )
        page = build_page(
            [run_event_info_from_domain(event) for event in events],
            page_request,
            next_cursor,
        )
        return RunEventPage(items=page.items, next_cursor=page.next_cursor, has_more=page.has_more)


class ListRunEventsForActorHandler:
    def __init__(self, list_events_handler: ListRunEventsHandler) -> None:
        self._list_events_handler = list_events_handler

    async def handle(self, query: ListRunEventsForActorQuery) -> RunEventPage:
        require_read_runs(query.actor)
        return await self._list_events_handler.handle(
            ListRunEventsQuery(
                team_id=query.actor.team_id,
                run_id=query.run_id,
                cursor=query.cursor,
                limit=query.limit,
            )
        )


class RunReaderService(RunReader):
    def __init__(
        self,
        get_run_handler: GetRunHandler,
        list_events_handler: ListRunEventsHandler,
    ) -> None:
        self._get_run_handler = get_run_handler
        self._list_events_handler = list_events_handler

    async def get_run(self, *, team_id: UUID, run_id: UUID) -> RunInfo:
        return await self._get_run_handler.handle(GetRunQuery(team_id=team_id, run_id=run_id))

    async def list_events(
        self,
        *,
        team_id: UUID,
        run_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> RunEventPage:
        return await self._list_events_handler.handle(
            ListRunEventsQuery(team_id=team_id, run_id=run_id, cursor=cursor, limit=limit)
        )
