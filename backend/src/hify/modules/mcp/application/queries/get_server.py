from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.mcp.application.authorization import require_read_mcp
from hify.modules.mcp.application.dto import mcp_server_info_from_domain
from hify.modules.mcp.application.ports import McpUnitOfWorkFactory
from hify.modules.mcp.contracts.dto import McpServerInfo
from hify.modules.mcp.contracts.services import McpServerCatalog
from hify.modules.mcp.domain.errors import McpServerNotFoundError


@dataclass(frozen=True, slots=True)
class GetMcpServerQuery:
    team_id: UUID
    server_id: UUID


@dataclass(frozen=True, slots=True)
class GetMcpServerForActorQuery:
    actor: ActorContext
    server_id: UUID


class GetMcpServerHandler:
    def __init__(self, unit_of_work_factory: McpUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetMcpServerQuery) -> McpServerInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            server = await unit_of_work.servers.get_by_id(query.server_id)
        if server is None or server.team_id != query.team_id:
            raise McpServerNotFoundError("mcp server was not found")
        return mcp_server_info_from_domain(server)


class GetMcpServerForActorHandler:
    def __init__(self, get_server_handler: GetMcpServerHandler) -> None:
        self._get_server_handler = get_server_handler

    async def handle(self, query: GetMcpServerForActorQuery) -> McpServerInfo:
        require_read_mcp(query.actor)
        return await self._get_server_handler.handle(
            GetMcpServerQuery(team_id=query.actor.team_id, server_id=query.server_id)
        )


class ListMcpServersForActorHandler:
    def __init__(self, unit_of_work_factory: McpUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, *, actor: ActorContext) -> tuple[McpServerInfo, ...]:
        require_read_mcp(actor)
        async with self._unit_of_work_factory() as unit_of_work:
            servers = await unit_of_work.servers.list_by_team(actor.team_id)
        return tuple(mcp_server_info_from_domain(server) for server in servers)


class McpServerCatalogService(McpServerCatalog):
    def __init__(self, unit_of_work_factory: McpUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def get_server(self, *, team_id: UUID, server_id: UUID) -> McpServerInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            server = await unit_of_work.servers.get_by_id(server_id)
        if server is None or server.team_id != team_id:
            raise McpServerNotFoundError("mcp server was not found")
        return mcp_server_info_from_domain(server)

    async def list_servers(self, *, team_id: UUID) -> tuple[McpServerInfo, ...]:
        async with self._unit_of_work_factory() as unit_of_work:
            servers = await unit_of_work.servers.list_by_team(team_id)
        return tuple(mcp_server_info_from_domain(server) for server in servers)
