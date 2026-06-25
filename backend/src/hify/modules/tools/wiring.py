from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.mcp.contracts.services import McpToolDiscovery, McpToolInvoker
from hify.modules.tools.api.dependencies import (
    AuthenticationNotConfiguredAuthenticator,
    RequestAuthenticator,
)
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
from hify.modules.tools.infrastructure.adapters.web_search import (
    DuckDuckGoWebSearchTool,
    WEB_SEARCH_BUILTIN_NAME,
)
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
    mcp_tool_discovery: McpToolDiscovery,
    mcp_tool_invoker: McpToolInvoker,
    clock: Clock | None = None,
    request_authenticator: RequestAuthenticator | None = None,
    web_search_enabled: bool = True,
    web_search_timeout_seconds: float = 10.0,
    web_search_max_results: int = 5,
) -> ToolsModule:
    module_clock = clock or SystemClock()

    def unit_of_work_factory() -> SqlAlchemyToolsUnitOfWork:
        return SqlAlchemyToolsUnitOfWork(session_factory)

    create_tool_handler = CreateToolHandler(
        unit_of_work_factory,
        module_clock,
        mcp_tool_discovery,
    )
    get_tool_handler = GetToolHandler(unit_of_work_factory)
    get_tool_for_actor_handler = GetToolForActorHandler(get_tool_handler)
    list_tools_for_actor_handler = ListToolsForActorHandler(unit_of_work_factory)
    tool_catalog = ToolCatalogService(get_tool_handler, unit_of_work_factory)
    builtin_tool_handlers = {}
    if web_search_enabled:
        web_search_tool = DuckDuckGoWebSearchTool(
            timeout_seconds=web_search_timeout_seconds,
            default_max_results=web_search_max_results,
        )
        builtin_tool_handlers[WEB_SEARCH_BUILTIN_NAME] = web_search_tool.invoke
    tool_executor = ToolRuntimeExecutor(
        unit_of_work_factory,
        EmptyBuiltinToolInvoker(builtin_tool_handlers),
        HttpxToolInvoker(),
        mcp_tool_invoker,
    )
    router = create_tools_router(
        create_tool_handler=create_tool_handler,
        get_tool_handler=get_tool_for_actor_handler,
        list_tools_handler=list_tools_for_actor_handler,
        request_authenticator=request_authenticator or AuthenticationNotConfiguredAuthenticator(),
    )
    return ToolsModule(router=router, tool_catalog=tool_catalog, tool_executor=tool_executor)
