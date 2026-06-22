from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.tools.application.authorization import require_read_tools
from hify.modules.tools.application.dto import tool_info_from_domain
from hify.modules.tools.application.ports import ToolsUnitOfWorkFactory
from hify.modules.tools.contracts.dto import ToolInfo
from hify.modules.tools.contracts.services import ToolCatalog
from hify.modules.tools.domain.errors import ToolNotFoundError


@dataclass(frozen=True, slots=True)
class GetToolQuery:
    team_id: UUID
    tool_id: UUID


@dataclass(frozen=True, slots=True)
class GetToolForActorQuery:
    actor: ActorContext
    tool_id: UUID


class GetToolHandler:
    def __init__(self, unit_of_work_factory: ToolsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetToolQuery) -> ToolInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            tool = await unit_of_work.tools.get_by_id(query.tool_id)
        if tool is None or tool.team_id != query.team_id:
            raise ToolNotFoundError("tool was not found")
        return tool_info_from_domain(tool)


class GetToolForActorHandler:
    def __init__(self, get_tool_handler: GetToolHandler) -> None:
        self._get_tool_handler = get_tool_handler

    async def handle(self, query: GetToolForActorQuery) -> ToolInfo:
        require_read_tools(query.actor)
        return await self._get_tool_handler.handle(
            GetToolQuery(team_id=query.actor.team_id, tool_id=query.tool_id)
        )


class ListToolsForActorHandler:
    def __init__(self, unit_of_work_factory: ToolsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, *, actor: ActorContext) -> tuple[ToolInfo, ...]:
        require_read_tools(actor)
        async with self._unit_of_work_factory() as unit_of_work:
            tools = await unit_of_work.tools.list_by_team(actor.team_id)
        return tuple(tool_info_from_domain(tool) for tool in tools)


class ToolCatalogService(ToolCatalog):
    def __init__(
        self,
        get_tool_handler: GetToolHandler,
        unit_of_work_factory: ToolsUnitOfWorkFactory,
    ) -> None:
        self._get_tool_handler = get_tool_handler
        self._unit_of_work_factory = unit_of_work_factory

    async def get_tool(self, *, team_id: UUID, tool_id: UUID) -> ToolInfo:
        return await self._get_tool_handler.handle(GetToolQuery(team_id=team_id, tool_id=tool_id))

    async def list_tools(self, *, team_id: UUID) -> tuple[ToolInfo, ...]:
        async with self._unit_of_work_factory() as unit_of_work:
            tools = await unit_of_work.tools.list_by_team(team_id)
        return tuple(tool_info_from_domain(tool) for tool in tools)
