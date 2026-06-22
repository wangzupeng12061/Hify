from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.usage.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.usage.api.router import create_usage_router
from hify.modules.usage.application.commands.record_model_usage import (
    RecordModelUsageHandler,
    UsageRecorderService,
)
from hify.modules.usage.application.queries.get_run_usage_summary import GetRunUsageSummaryHandler
from hify.modules.usage.application.queries.get_team_usage_summary import GetTeamUsageSummaryHandler
from hify.modules.usage.application.queries.usage_reader import UsageReaderService
from hify.modules.usage.contracts.services import UsageReader, UsageRecorder
from hify.modules.usage.infrastructure.database.uow import SqlAlchemyUsageUnitOfWork
from hify.shared.domain.clock import Clock, SystemClock


@dataclass(frozen=True, slots=True)
class UsageModule:
    router: APIRouter
    usage_recorder: UsageRecorder
    usage_reader: UsageReader


def create_usage_module(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    clock: Clock | None = None,
) -> UsageModule:
    module_clock = clock or SystemClock()

    def unit_of_work_factory() -> SqlAlchemyUsageUnitOfWork:
        return SqlAlchemyUsageUnitOfWork(session_factory)

    record_model_usage_handler = RecordModelUsageHandler(unit_of_work_factory, module_clock)
    get_team_summary_handler = GetTeamUsageSummaryHandler(unit_of_work_factory)
    get_run_summary_handler = GetRunUsageSummaryHandler(unit_of_work_factory)
    usage_recorder = UsageRecorderService(record_model_usage_handler)
    usage_reader = UsageReaderService(unit_of_work_factory)
    router = create_usage_router(
        get_team_summary_handler=get_team_summary_handler,
        get_run_summary_handler=get_run_summary_handler,
        request_authenticator=AuthenticationNotConfiguredAuthenticator(),
    )
    return UsageModule(
        router=router,
        usage_recorder=usage_recorder,
        usage_reader=usage_reader,
    )
