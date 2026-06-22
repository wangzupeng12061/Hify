from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.tools.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.tools.api.router import create_tools_router
from hify.modules.tools.application.commands.create_tool import CreateToolHandler
from hify.modules.tools.application.executor import ToolRuntimeExecutor
from hify.modules.tools.application.queries.get_tool import (
    GetToolForActorHandler,
    GetToolHandler,
    ListToolsForActorHandler,
    ToolCatalogService,
)
from hify.modules.tools.contracts.services import ToolCatalog, ToolExecutor
from hify.modules.tools.infrastructure.adapters.builtin import EmptyBuiltinToolInvoker
from hify.modules.tools.infrastructure.adapters.http import HttpxToolInvoker
from hify.modules.tools.infrastructure.database.uow import SqlAlchemyToolsUnitOfWork
from hify.shared.domain.clock import Clock, SystemClock


@dataclass(frozen=True, slots=True)
class ToolsModule:
    router: APIRouter
    tool_catalog: ToolCatalog
    tool_executor: ToolExecutor


def create_tools_module(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    clock: Clock | None = None,
) -> ToolsModule:
    module_clock = clock or SystemClock()

    def unit_of_work_factory() -> SqlAlchemyToolsUnitOfWork:
        return SqlAlchemyToolsUnitOfWork(session_factory)

    create_tool_handler = CreateToolHandler(unit_of_work_factory, module_clock)
    get_tool_handler = GetToolHandler(unit_of_work_factory)
    get_tool_for_actor_handler = GetToolForActorHandler(get_tool_handler)
    list_tools_for_actor_handler = ListToolsForActorHandler(unit_of_work_factory)
    tool_catalog = ToolCatalogService(get_tool_handler, unit_of_work_factory)
    tool_executor = ToolRuntimeExecutor(
        unit_of_work_factory,
        EmptyBuiltinToolInvoker(),
        HttpxToolInvoker(),
    )
    router = create_tools_router(
        create_tool_handler=create_tool_handler,
        get_tool_handler=get_tool_for_actor_handler,
        list_tools_handler=list_tools_for_actor_handler,
        request_authenticator=AuthenticationNotConfiguredAuthenticator(),
    )
    return ToolsModule(router=router, tool_catalog=tool_catalog, tool_executor=tool_executor)
