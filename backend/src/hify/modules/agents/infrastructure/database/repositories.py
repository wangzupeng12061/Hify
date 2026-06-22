from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.agents.domain.entities import Agent, AgentVersion
from hify.modules.agents.domain.value_objects import AgentStatus
from hify.modules.agents.infrastructure.database.models import AgentModel, AgentVersionModel


class SqlAlchemyAgentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, agent: Agent) -> None:
        self._session.add(_agent_to_model(agent))

    async def save(self, agent: Agent) -> None:
        model = await self._session.get(AgentModel, agent.id)
        if model is None:
            self._session.add(_agent_to_model(agent))
            return
        model.name = agent.name
        model.description = agent.description
        model.system_prompt = agent.system_prompt
        model.provider_model_id = agent.provider_model_id
        model.knowledge_base_ids = list(agent.knowledge_base_ids)
        model.workflow_id = agent.workflow_id
        model.status = agent.status.value
        model.latest_version_number = agent.latest_version_number
        model.version = agent.version
        model.updated_at = agent.updated_at

    async def get_by_id(self, agent_id: UUID) -> Agent | None:
        model = await self._session.get(AgentModel, agent_id)
        if model is None:
            return None
        return _agent_from_model(model)

    async def get_by_team_and_name(self, *, team_id: UUID, name: str) -> Agent | None:
        statement = select(AgentModel).where(
            AgentModel.team_id == team_id,
            func.lower(AgentModel.name) == name.lower(),
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _agent_from_model(model)


class SqlAlchemyAgentVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, agent_version: AgentVersion) -> None:
        self._session.add(_agent_version_to_model(agent_version))

    async def get_by_id(self, agent_version_id: UUID) -> AgentVersion | None:
        model = await self._session.get(AgentVersionModel, agent_version_id)
        if model is None:
            return None
        return _agent_version_from_model(model)

    async def get_latest_by_agent_id(self, agent_id: UUID) -> AgentVersion | None:
        statement = (
            select(AgentVersionModel)
            .where(AgentVersionModel.agent_id == agent_id)
            .order_by(AgentVersionModel.version_number.desc())
            .limit(1)
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _agent_version_from_model(model)


def _agent_to_model(agent: Agent) -> AgentModel:
    return AgentModel(
        id=agent.id,
        team_id=agent.team_id,
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        provider_model_id=agent.provider_model_id,
        knowledge_base_ids=list(agent.knowledge_base_ids),
        workflow_id=agent.workflow_id,
        status=agent.status.value,
        latest_version_number=agent.latest_version_number,
        version=agent.version,
        created_by=agent.created_by,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


def _agent_from_model(model: AgentModel) -> Agent:
    return Agent(
        id=model.id,
        team_id=model.team_id,
        name=model.name,
        description=model.description,
        system_prompt=model.system_prompt,
        provider_model_id=model.provider_model_id,
        knowledge_base_ids=tuple(model.knowledge_base_ids),
        workflow_id=model.workflow_id,
        status=AgentStatus(model.status),
        latest_version_number=model.latest_version_number,
        version=model.version,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _agent_version_to_model(agent_version: AgentVersion) -> AgentVersionModel:
    return AgentVersionModel(
        id=agent_version.id,
        team_id=agent_version.team_id,
        agent_id=agent_version.agent_id,
        version_number=agent_version.version_number,
        name=agent_version.name,
        description=agent_version.description,
        system_prompt=agent_version.system_prompt,
        knowledge_base_ids=list(agent_version.knowledge_base_ids),
        workflow_id=agent_version.workflow_id,
        workflow_version_id=agent_version.workflow_version_id,
        workflow_version_number=agent_version.workflow_version_number,
        workflow_name=agent_version.workflow_name,
        workflow_definition=(
            dict(agent_version.workflow_definition)
            if agent_version.workflow_definition is not None
            else None
        ),
        provider_model_id=agent_version.provider_model_id,
        provider_type=agent_version.provider_type,
        provider_name=agent_version.provider_name,
        model_name=agent_version.model_name,
        model_display_name=agent_version.model_display_name,
        context_window_tokens=agent_version.context_window_tokens,
        supports_tools=agent_version.supports_tools,
        supports_vision=agent_version.supports_vision,
        supports_structured_output=agent_version.supports_structured_output,
        published_by=agent_version.published_by,
        created_at=agent_version.created_at,
    )


def _agent_version_from_model(model: AgentVersionModel) -> AgentVersion:
    return AgentVersion(
        id=model.id,
        team_id=model.team_id,
        agent_id=model.agent_id,
        version_number=model.version_number,
        name=model.name,
        description=model.description,
        system_prompt=model.system_prompt,
        knowledge_base_ids=tuple(model.knowledge_base_ids),
        workflow_id=model.workflow_id,
        workflow_version_id=model.workflow_version_id,
        workflow_version_number=model.workflow_version_number,
        workflow_name=model.workflow_name,
        workflow_definition=(
            dict(model.workflow_definition) if model.workflow_definition is not None else None
        ),
        provider_model_id=model.provider_model_id,
        provider_type=model.provider_type,
        provider_name=model.provider_name,
        model_name=model.model_name,
        model_display_name=model.model_display_name,
        context_window_tokens=model.context_window_tokens,
        supports_tools=model.supports_tools,
        supports_vision=model.supports_vision,
        supports_structured_output=model.supports_structured_output,
        published_by=model.published_by,
        created_at=model.created_at,
    )
