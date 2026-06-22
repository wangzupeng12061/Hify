from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.agents.application.dto import agent_version_info_from_domain
from hify.modules.agents.application.ports import AgentsUnitOfWorkFactory
from hify.modules.agents.contracts.dto import AgentVersionInfo
from hify.modules.agents.contracts.services import AgentCatalog
from hify.modules.agents.domain.errors import AgentVersionNotFoundError


@dataclass(frozen=True, slots=True)
class GetAgentVersionQuery:
    team_id: UUID
    agent_version_id: UUID


@dataclass(frozen=True, slots=True)
class GetLatestPublishedAgentVersionQuery:
    team_id: UUID
    agent_id: UUID


class GetAgentVersionHandler:
    def __init__(self, unit_of_work_factory: AgentsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetAgentVersionQuery) -> AgentVersionInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            agent_version = await unit_of_work.versions.get_by_id(query.agent_version_id)
        if agent_version is None or agent_version.team_id != query.team_id:
            raise AgentVersionNotFoundError("agent version was not found")
        return agent_version_info_from_domain(agent_version)


class GetLatestPublishedAgentVersionHandler:
    def __init__(self, unit_of_work_factory: AgentsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetLatestPublishedAgentVersionQuery) -> AgentVersionInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            agent = await unit_of_work.agents.get_by_id(query.agent_id)
            if agent is None or agent.team_id != query.team_id:
                raise AgentVersionNotFoundError("agent version was not found")
            agent_version = await unit_of_work.versions.get_latest_by_agent_id(query.agent_id)
        if agent_version is None or agent_version.team_id != query.team_id:
            raise AgentVersionNotFoundError("agent version was not found")
        return agent_version_info_from_domain(agent_version)


class AgentCatalogService(AgentCatalog):
    def __init__(
        self,
        get_agent_version_handler: GetAgentVersionHandler,
        get_latest_published_agent_version_handler: GetLatestPublishedAgentVersionHandler,
    ) -> None:
        self._get_agent_version_handler = get_agent_version_handler
        self._get_latest_published_agent_version_handler = (
            get_latest_published_agent_version_handler
        )

    async def get_latest_published_version(
        self,
        *,
        team_id: UUID,
        agent_id: UUID,
    ) -> AgentVersionInfo:
        return await self._get_latest_published_agent_version_handler.handle(
            GetLatestPublishedAgentVersionQuery(team_id=team_id, agent_id=agent_id)
        )

    async def get_agent_version(
        self,
        *,
        team_id: UUID,
        agent_version_id: UUID,
    ) -> AgentVersionInfo:
        return await self._get_agent_version_handler.handle(
            GetAgentVersionQuery(team_id=team_id, agent_version_id=agent_version_id)
        )
