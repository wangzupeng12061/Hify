from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.tools.application.authorization import require_manage_tools
from hify.modules.tools.application.dto import tool_info_from_domain
from hify.modules.tools.application.ports import ToolsUnitOfWorkFactory
from hify.modules.tools.contracts.dto import ToolInfo
from hify.modules.tools.domain.entities import ToolDefinition
from hify.modules.tools.domain.errors import ToolAlreadyExistsError
from hify.modules.tools.domain.value_objects import (
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


class CreateToolHandler:
    def __init__(
        self,
        unit_of_work_factory: ToolsUnitOfWorkFactory,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: CreateToolCommand) -> ToolInfo:
        require_manage_tools(command.actor)
        tool_name = normalize_tool_name(command.name)
        tool_kind = parse_tool_kind(command.tool_kind)
        http_method = parse_http_tool_method(command.http_method)
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
                input_schema=command.input_schema,
                builtin_name=command.builtin_name,
                endpoint_url=command.endpoint_url,
                http_method=http_method,
                http_headers=command.http_headers,
                created_by=command.actor.user_id,
                now=now,
            )
            await unit_of_work.tools.add(tool)
            await unit_of_work.commit()

        return tool_info_from_domain(tool)
