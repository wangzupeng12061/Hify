from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.agents.contracts.services import AgentCatalog
from hify.modules.conversations.contracts.services import ConversationReader
from hify.modules.runs.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.runs.api.router import create_runs_router
from hify.modules.runs.application.commands.cancel_run import CancelRunHandler
from hify.modules.runs.application.commands.create_run import CreateRunHandler
from hify.modules.runs.application.queries.get_run import GetRunForActorHandler, GetRunHandler
from hify.modules.runs.application.queries.list_run_events import (
    ListRunEventsForActorHandler,
    ListRunEventsHandler,
    RunReaderService,
)
from hify.modules.runs.contracts.services import RunReader
from hify.modules.runs.infrastructure.database.uow import SqlAlchemyRunsUnitOfWork
from hify.shared.domain.clock import Clock, SystemClock


@dataclass(frozen=True, slots=True)
class RunsModule:
    router: APIRouter
    run_reader: RunReader


def create_runs_module(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    conversation_reader: ConversationReader,
    agent_catalog: AgentCatalog,
    clock: Clock | None = None,
) -> RunsModule:
    module_clock = clock or SystemClock()

    def unit_of_work_factory() -> SqlAlchemyRunsUnitOfWork:
        return SqlAlchemyRunsUnitOfWork(session_factory)

    create_run_handler = CreateRunHandler(
        unit_of_work_factory,
        conversation_reader,
        agent_catalog,
        module_clock,
    )
    cancel_run_handler = CancelRunHandler(unit_of_work_factory, module_clock)
    get_run_handler = GetRunHandler(unit_of_work_factory)
    get_run_for_actor_handler = GetRunForActorHandler(get_run_handler)
    list_events_handler = ListRunEventsHandler(unit_of_work_factory)
    list_events_for_actor_handler = ListRunEventsForActorHandler(list_events_handler)
    run_reader = RunReaderService(get_run_handler, list_events_handler)
    router = create_runs_router(
        create_run_handler=create_run_handler,
        cancel_run_handler=cancel_run_handler,
        get_run_handler=get_run_for_actor_handler,
        list_events_handler=list_events_for_actor_handler,
        request_authenticator=AuthenticationNotConfiguredAuthenticator(),
    )
    return RunsModule(router=router, run_reader=run_reader)
