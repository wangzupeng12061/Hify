from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.agents.application.authorization import require_manage_agents
from hify.modules.agents.application.dto import agent_info_from_domain
from hify.modules.agents.application.model_binding import model_binding_snapshot_from_model_info
from hify.modules.agents.application.ports import AgentsUnitOfWorkFactory
from hify.modules.agents.contracts.dto import AgentInfo
from hify.modules.agents.domain.entities import Agent
from hify.modules.agents.domain.errors import AgentAlreadyExistsError
from hify.modules.agents.domain.value_objects import normalize_agent_name
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.knowledge.contracts.services import KnowledgeBaseCatalog
from hify.modules.providers.contracts.services import ModelCatalog
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class CreateAgentCommand:
    actor: ActorContext
    name: str
    description: str | None
    system_prompt: str
    provider_model_id: UUID
    knowledge_base_ids: tuple[UUID, ...] = ()


class CreateAgentHandler:
    def __init__(
        self,
        unit_of_work_factory: AgentsUnitOfWorkFactory,
        model_catalog: ModelCatalog,
        knowledge_base_catalog: KnowledgeBaseCatalog,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._model_catalog = model_catalog
        self._knowledge_base_catalog = knowledge_base_catalog
        self._clock = clock

    async def handle(self, command: CreateAgentCommand) -> AgentInfo:
        require_manage_agents(command.actor)
        agent_name = normalize_agent_name(command.name)
        model = await self._model_catalog.get_model(
            team_id=command.actor.team_id,
            model_id=command.provider_model_id,
        )
        model_binding_snapshot_from_model_info(model)
        for knowledge_base_id in command.knowledge_base_ids:
            await self._knowledge_base_catalog.get_knowledge_base(
                team_id=command.actor.team_id,
                knowledge_base_id=knowledge_base_id,
            )
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            existing_agent = await unit_of_work.agents.get_by_team_and_name(
                team_id=command.actor.team_id,
                name=agent_name,
            )
            if existing_agent is not None:
                raise AgentAlreadyExistsError("agent already exists")

            agent = Agent.create(
                team_id=command.actor.team_id,
                name=agent_name,
                description=command.description,
                system_prompt=command.system_prompt,
                provider_model_id=command.provider_model_id,
                knowledge_base_ids=command.knowledge_base_ids,
                created_by=command.actor.user_id,
                now=now,
            )
            await unit_of_work.agents.add(agent)
            await unit_of_work.commit()

        return agent_info_from_domain(agent)
