from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.mcp.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.mcp.api.router import create_mcp_router
from hify.modules.mcp.application.commands.create_server import CreateMcpServerHandler
from hify.modules.mcp.application.commands.refresh_tools import (
    McpToolDiscoveryService,
    RefreshMcpToolsHandler,
)
from hify.modules.mcp.application.invoker import McpToolInvokerService
from hify.modules.mcp.application.queries.get_server import (
    GetMcpServerForActorHandler,
    GetMcpServerHandler,
    ListMcpServersForActorHandler,
    McpServerCatalogService,
)
from hify.modules.mcp.application.queries.list_tools import ListMcpToolsForActorHandler
from hify.modules.mcp.contracts.services import McpServerCatalog, McpToolDiscovery, McpToolInvoker
from hify.modules.mcp.infrastructure.adapters.unavailable import UnavailableMcpClient
from hify.modules.mcp.infrastructure.database.uow import SqlAlchemyMcpUnitOfWork
from hify.shared.domain.clock import Clock, SystemClock


@dataclass(frozen=True, slots=True)
class McpModule:
    router: APIRouter
    mcp_server_catalog: McpServerCatalog
    mcp_tool_discovery: McpToolDiscovery
    mcp_tool_invoker: McpToolInvoker


def create_mcp_module(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    clock: Clock | None = None,
) -> McpModule:
    module_clock = clock or SystemClock()
    mcp_client = UnavailableMcpClient()

    def unit_of_work_factory() -> SqlAlchemyMcpUnitOfWork:
        return SqlAlchemyMcpUnitOfWork(session_factory)

    create_server_handler = CreateMcpServerHandler(unit_of_work_factory, module_clock)
    get_server_handler = GetMcpServerHandler(unit_of_work_factory)
    get_server_for_actor_handler = GetMcpServerForActorHandler(get_server_handler)
    list_servers_handler = ListMcpServersForActorHandler(unit_of_work_factory)
    list_tools_handler = ListMcpToolsForActorHandler(unit_of_work_factory)
    refresh_tools_handler = RefreshMcpToolsHandler(
        unit_of_work_factory,
        mcp_client,
        module_clock,
    )
    mcp_server_catalog = McpServerCatalogService(unit_of_work_factory)
    mcp_tool_discovery = McpToolDiscoveryService(unit_of_work_factory, refresh_tools_handler)
    mcp_tool_invoker = McpToolInvokerService(unit_of_work_factory, mcp_client)
    router = create_mcp_router(
        create_server_handler=create_server_handler,
        get_server_handler=get_server_for_actor_handler,
        list_servers_handler=list_servers_handler,
        list_tools_handler=list_tools_handler,
        refresh_tools_handler=refresh_tools_handler,
        request_authenticator=AuthenticationNotConfiguredAuthenticator(),
    )
    return McpModule(
        router=router,
        mcp_server_catalog=mcp_server_catalog,
        mcp_tool_discovery=mcp_tool_discovery,
        mcp_tool_invoker=mcp_tool_invoker,
    )
