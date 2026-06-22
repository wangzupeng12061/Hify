from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.agents.application.authorization import require_manage_agents
from hify.modules.agents.application.dto import agent_version_info_from_domain
from hify.modules.agents.application.model_binding import model_binding_snapshot_from_model_info
from hify.modules.agents.application.ports import AgentsUnitOfWorkFactory
from hify.modules.agents.contracts.dto import AgentVersionInfo
from hify.modules.agents.domain.errors import AgentNotFoundError
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.providers.contracts.services import ModelCatalog
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class PublishAgentCommand:
    actor: ActorContext
    agent_id: UUID


class PublishAgentHandler:
    def __init__(
        self,
        unit_of_work_factory: AgentsUnitOfWorkFactory,
        model_catalog: ModelCatalog,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._model_catalog = model_catalog
        self._clock = clock

    async def handle(self, command: PublishAgentCommand) -> AgentVersionInfo:
        require_manage_agents(command.actor)
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            agent = await unit_of_work.agents.get_by_id(command.agent_id)
            if agent is None or agent.team_id != command.actor.team_id:
                raise AgentNotFoundError("agent was not found")

            model = await self._model_catalog.get_model(
                team_id=command.actor.team_id,
                model_id=agent.provider_model_id,
            )
            model_snapshot = model_binding_snapshot_from_model_info(model)
            agent_version = agent.publish(
                model_snapshot=model_snapshot,
                published_by=command.actor.user_id,
                now=now,
            )
            await unit_of_work.versions.add(agent_version)
            await unit_of_work.commit()

        return agent_version_info_from_domain(agent_version)
