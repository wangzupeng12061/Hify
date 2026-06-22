from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.mcp.contracts.dto import McpToolInfo
from hify.modules.mcp.contracts.services import McpToolDiscovery
from hify.modules.tools.application.authorization import require_manage_tools
from hify.modules.tools.application.dto import tool_info_from_domain
from hify.modules.tools.application.ports import ToolsUnitOfWorkFactory
from hify.modules.tools.contracts.dto import ToolInfo
from hify.modules.tools.domain.entities import ToolDefinition
from hify.modules.tools.domain.errors import ToolAlreadyExistsError, ToolValidationError
from hify.modules.tools.domain.value_objects import (
    ToolKind,
    normalize_tool_name,
    parse_http_tool_method,
    parse_tool_kind,
)
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class CreateToolCommand:
    actor: ActorContext
    name: str
    description: str | None
    tool_kind: str
    input_schema: Mapping[str, object]
    builtin_name: str | None
    endpoint_url: str | None
    http_method: str | None
    http_headers: Mapping[str, str]
    mcp_server_id: UUID | None = None
    mcp_tool_id: UUID | None = None
    mcp_tool_name: str | None = None


class CreateToolHandler:
    def __init__(
        self,
        unit_of_work_factory: ToolsUnitOfWorkFactory,
        clock: Clock,
        mcp_tool_discovery: McpToolDiscovery | None = None,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._mcp_tool_discovery = mcp_tool_discovery

    async def handle(self, command: CreateToolCommand) -> ToolInfo:
        require_manage_tools(command.actor)
        tool_name = normalize_tool_name(command.name)
        tool_kind = parse_tool_kind(command.tool_kind)
        http_method = parse_http_tool_method(command.http_method)
        mcp_tool = await self._get_mcp_tool(command, tool_kind)
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            existing_tool = await unit_of_work.tools.get_by_team_and_name(
                team_id=command.actor.team_id,
                name=tool_name,
            )
            if existing_tool is not None:
                raise ToolAlreadyExistsError("tool already exists")

            tool = ToolDefinition.create(
                team_id=command.actor.team_id,
                name=tool_name,
                description=command.description,
                tool_kind=tool_kind,
                input_schema=mcp_tool.input_schema if mcp_tool is not None else command.input_schema,
                builtin_name=command.builtin_name,
                endpoint_url=command.endpoint_url,
                http_method=http_method,
                http_headers=command.http_headers,
                mcp_server_id=mcp_tool.server_id if mcp_tool is not None else command.mcp_server_id,
                mcp_tool_id=mcp_tool.id if mcp_tool is not None else command.mcp_tool_id,
                mcp_tool_name=mcp_tool.name if mcp_tool is not None else command.mcp_tool_name,
                created_by=command.actor.user_id,
                now=now,
            )
            await unit_of_work.tools.add(tool)
            await unit_of_work.commit()

        return tool_info_from_domain(tool)

    async def _get_mcp_tool(
        self,
        command: CreateToolCommand,
        tool_kind: ToolKind,
    ) -> McpToolInfo | None:
        if tool_kind is not ToolKind.MCP:
            return None
        if self._mcp_tool_discovery is None:
            raise ToolValidationError("mcp tool discovery is not configured")
        if command.mcp_server_id is None:
            raise ToolValidationError("mcp tools require an mcp server id")
        if command.mcp_tool_id is None:
            raise ToolValidationError("mcp tools require an mcp tool id")
        mcp_tool = await self._mcp_tool_discovery.get_tool(
            team_id=command.actor.team_id,
            tool_id=command.mcp_tool_id,
        )
        if mcp_tool.server_id != command.mcp_server_id:
            raise ToolValidationError("mcp tool does not belong to the selected server")
        if mcp_tool.status != "active":
            raise ToolValidationError("mcp tool is not active")
        if command.mcp_tool_name is not None and command.mcp_tool_name != mcp_tool.name:
            raise ToolValidationError("mcp tool name does not match discovered tool")
        return mcp_tool
