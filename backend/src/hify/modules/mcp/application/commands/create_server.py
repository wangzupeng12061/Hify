from __future__ import annotations

from dataclasses import dataclass

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.mcp.application.authorization import require_manage_mcp
from hify.modules.mcp.application.dto import mcp_server_info_from_domain
from hify.modules.mcp.application.ports import McpUnitOfWorkFactory
from hify.modules.mcp.contracts.dto import McpServerInfo
from hify.modules.mcp.domain.entities import McpServer
from hify.modules.mcp.domain.errors import McpServerAlreadyExistsError
from hify.modules.mcp.domain.value_objects import normalize_server_name
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class CreateMcpServerCommand:
    actor: ActorContext
    name: str
    description: str | None
    transport: str
    endpoint_url: str


class CreateMcpServerHandler:
    def __init__(self, unit_of_work_factory: McpUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: CreateMcpServerCommand) -> McpServerInfo:
        require_manage_mcp(command.actor)
        server_name = normalize_server_name(command.name)
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            existing = await unit_of_work.servers.get_by_team_and_name(
                team_id=command.actor.team_id,
                name=server_name,
            )
            if existing is not None:
                raise McpServerAlreadyExistsError("mcp server already exists")

            server = McpServer.create(
                team_id=command.actor.team_id,
                name=server_name,
                description=command.description,
                transport=command.transport,
                endpoint_url=command.endpoint_url,
                created_by=command.actor.user_id,
                now=now,
            )
            await unit_of_work.servers.add(server)
            await unit_of_work.commit()
            return mcp_server_info_from_domain(server)
