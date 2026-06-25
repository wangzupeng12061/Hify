from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.agents.contracts.services import AgentCatalog
from hify.modules.conversations.contracts.services import ConversationReader, ConversationWriter
from hify.modules.knowledge.contracts.services import KnowledgeRetriever
from hify.modules.providers.contracts.services import ModelGateway
from hify.modules.runs.api.dependencies import (
    AuthenticationNotConfiguredAuthenticator,
    RequestAuthenticator,
)
from hify.modules.runs.api.router import create_runs_router
from hify.modules.runs.application.commands.cancel_run import CancelRunHandler
from hify.modules.runs.application.commands.create_run import CreateRunHandler
from hify.modules.runs.application.executor import RunExecutor
from hify.modules.runs.application.queries.get_run import GetRunForActorHandler, GetRunHandler
from hify.modules.runs.application.queries.get_run_diagnostics import GetRunDiagnosticsHandler
from hify.modules.runs.application.queries.list_run_events import (
    ListRunEventsForActorHandler,
    ListRunEventsHandler,
    RunReaderService,
)
from hify.modules.runs.contracts.services import RunReader
from hify.modules.runs.infrastructure.database.uow import SqlAlchemyRunsUnitOfWork
from hify.modules.tools.contracts.services import ToolCatalog, ToolExecutor
from hify.modules.usage.contracts.services import UsageQuotaChecker, UsageReader, UsageRecorder
from hify.shared.domain.clock import Clock, SystemClock


@dataclass(frozen=True, slots=True)
class RunsModule:
    router: APIRouter
    run_reader: RunReader
    run_executor: RunExecutor


def create_runs_module(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    conversation_reader: ConversationReader,
    conversation_writer: ConversationWriter,
    agent_catalog: AgentCatalog,
    model_gateway: ModelGateway,
    tool_catalog: ToolCatalog,
    tool_executor: ToolExecutor,
    knowledge_retriever: KnowledgeRetriever,
    usage_recorder: UsageRecorder,
    usage_reader: UsageReader,
    usage_quota_checker: UsageQuotaChecker,
    clock: Clock | None = None,
    request_authenticator: RequestAuthenticator | None = None,
) -> RunsModule:
    module_clock = clock or SystemClock()

    def unit_of_work_factory() -> SqlAlchemyRunsUnitOfWork:
        return SqlAlchemyRunsUnitOfWork(session_factory)

    create_run_handler = CreateRunHandler(
        unit_of_work_factory,
        conversation_reader,
        agent_catalog,
        usage_quota_checker,
        module_clock,
    )
    cancel_run_handler = CancelRunHandler(unit_of_work_factory, module_clock)
    get_run_handler = GetRunHandler(unit_of_work_factory)
    get_run_for_actor_handler = GetRunForActorHandler(get_run_handler)
    get_run_diagnostics_handler = GetRunDiagnosticsHandler(unit_of_work_factory, usage_reader)
    list_events_handler = ListRunEventsHandler(unit_of_work_factory)
    list_events_for_actor_handler = ListRunEventsForActorHandler(list_events_handler)
    run_reader = RunReaderService(get_run_handler, list_events_handler)
    run_executor = RunExecutor(
        unit_of_work_factory,
        conversation_reader,
        conversation_writer,
        agent_catalog,
        model_gateway,
        tool_executor,
        knowledge_retriever,
        usage_recorder,
        module_clock,
        tool_catalog=tool_catalog,
    )
    router = create_runs_router(
        create_run_handler=create_run_handler,
        cancel_run_handler=cancel_run_handler,
        get_run_handler=get_run_for_actor_handler,
        get_run_diagnostics_handler=get_run_diagnostics_handler,
        list_events_handler=list_events_for_actor_handler,
        run_executor=run_executor,
        request_authenticator=request_authenticator or AuthenticationNotConfiguredAuthenticator(),
    )
    return RunsModule(router=router, run_reader=run_reader, run_executor=run_executor)
