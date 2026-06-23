from __future__ import annotations

from dataclasses import dataclass

from hify.modules.agents.application.authorization import require_manage_agents
from hify.modules.agents.application.dto import agent_info_from_domain
from hify.modules.agents.application.ports import AgentsUnitOfWorkFactory
from hify.modules.agents.contracts.dto import AgentInfo
from hify.modules.identity.contracts.dto import ActorContext


@dataclass(frozen=True, slots=True)
class ListAgentsForActorQuery:
    actor: ActorContext


class ListAgentsForActorHandler:
    def __init__(self, unit_of_work_factory: AgentsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: ListAgentsForActorQuery) -> tuple[AgentInfo, ...]:
        require_manage_agents(query.actor)
        async with self._unit_of_work_factory() as unit_of_work:
            agents = await unit_of_work.agents.list_by_team(team_id=query.actor.team_id)

        return tuple(agent_info_from_domain(agent) for agent in agents)
