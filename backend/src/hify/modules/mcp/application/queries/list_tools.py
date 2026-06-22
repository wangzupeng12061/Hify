from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.mcp.application.authorization import require_read_mcp
from hify.modules.mcp.application.dto import mcp_tool_info_from_domain
from hify.modules.mcp.application.ports import McpUnitOfWorkFactory
from hify.modules.mcp.contracts.dto import McpToolInfo
from hify.modules.mcp.domain.errors import McpServerNotFoundError


@dataclass(frozen=True, slots=True)
class ListMcpToolsForActorQuery:
    actor: ActorContext
    server_id: UUID


class ListMcpToolsForActorHandler:
    def __init__(self, unit_of_work_factory: McpUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: ListMcpToolsForActorQuery) -> tuple[McpToolInfo, ...]:
        require_read_mcp(query.actor)
        async with self._unit_of_work_factory() as unit_of_work:
            server = await unit_of_work.servers.get_by_id(query.server_id)
            if server is None or server.team_id != query.actor.team_id:
                raise McpServerNotFoundError("mcp server was not found")
            tools = await unit_of_work.tools.list_by_server(
                team_id=query.actor.team_id,
                server_id=query.server_id,
            )
        return tuple(mcp_tool_info_from_domain(tool) for tool in tools)
