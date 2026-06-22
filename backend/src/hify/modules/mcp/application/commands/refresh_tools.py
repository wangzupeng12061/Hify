from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.mcp.application.authorization import require_manage_mcp
from hify.modules.mcp.application.dto import mcp_tool_info_from_domain
from hify.modules.mcp.application.ports import McpClient, McpUnitOfWorkFactory
from hify.modules.mcp.contracts.dto import McpToolInfo
from hify.modules.mcp.contracts.services import McpToolDiscovery
from hify.modules.mcp.domain.entities import McpDiscoveredTool
from hify.modules.mcp.domain.errors import McpServerNotFoundError
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class RefreshMcpToolsCommand:
    actor: ActorContext
    server_id: UUID


class RefreshMcpToolsHandler:
    def __init__(
        self,
        unit_of_work_factory: McpUnitOfWorkFactory,
        mcp_client: McpClient,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._mcp_client = mcp_client
        self._clock = clock

    async def handle(self, command: RefreshMcpToolsCommand) -> tuple[McpToolInfo, ...]:
        require_manage_mcp(command.actor)
        return await self.refresh_for_team(team_id=command.actor.team_id, server_id=command.server_id)

    async def refresh_for_team(self, *, team_id: UUID, server_id: UUID) -> tuple[McpToolInfo, ...]:
        async with self._unit_of_work_factory() as unit_of_work:
            server = await unit_of_work.servers.get_by_id(server_id)
        if server is None or server.team_id != team_id:
            raise McpServerNotFoundError("mcp server was not found")

        discovered_tools = await self._mcp_client.list_tools(server)
        now = self._clock.now()
        refreshed_tools: list[McpDiscoveredTool] = []

        async with self._unit_of_work_factory() as unit_of_work:
            current_server = await unit_of_work.servers.get_by_id(server_id)
            if current_server is None or current_server.team_id != team_id:
                raise McpServerNotFoundError("mcp server was not found")
            for discovered_tool in discovered_tools:
                existing_tool = await unit_of_work.tools.get_by_server_and_name(
                    server_id=current_server.id,
                    name=discovered_tool.name,
                )
                if existing_tool is None:
                    tool = McpDiscoveredTool.create(
                        team_id=current_server.team_id,
                        server_id=current_server.id,
                        name=discovered_tool.name,
                        description=discovered_tool.description,
                        input_schema=discovered_tool.input_schema,
                        now=now,
                    )
                    await unit_of_work.tools.add(tool)
                else:
                    existing_tool.update_from_discovery(
                        description=discovered_tool.description,
                        input_schema=discovered_tool.input_schema,
                        now=now,
                    )
                    await unit_of_work.tools.save(existing_tool)
                    tool = existing_tool
                refreshed_tools.append(tool)
            current_server.record_discovery(now=now)
            await unit_of_work.servers.save(current_server)
            await unit_of_work.commit()

        return tuple(mcp_tool_info_from_domain(tool) for tool in refreshed_tools)


class McpToolDiscoveryService(McpToolDiscovery):
    def __init__(
        self,
        unit_of_work_factory: McpUnitOfWorkFactory,
        refresh_tools_handler: RefreshMcpToolsHandler,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._refresh_tools_handler = refresh_tools_handler

    async def list_tools(self, *, team_id: UUID, server_id: UUID) -> tuple[McpToolInfo, ...]:
        async with self._unit_of_work_factory() as unit_of_work:
            server = await unit_of_work.servers.get_by_id(server_id)
            if server is None or server.team_id != team_id:
                raise McpServerNotFoundError("mcp server was not found")
            tools = await unit_of_work.tools.list_by_server(team_id=team_id, server_id=server_id)
        return tuple(mcp_tool_info_from_domain(tool) for tool in tools)

    async def refresh_tools(self, *, team_id: UUID, server_id: UUID) -> tuple[McpToolInfo, ...]:
        return await self._refresh_tools_handler.refresh_for_team(team_id=team_id, server_id=server_id)
