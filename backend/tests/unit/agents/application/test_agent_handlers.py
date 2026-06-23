from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from hify.modules.agents.application.commands.create_agent import (
    CreateAgentCommand,
    CreateAgentHandler,
)
from hify.modules.agents.application.commands.publish_agent import (
    PublishAgentCommand,
    PublishAgentHandler,
)
from hify.modules.agents.application.queries.get_agent_version import (
    AgentCatalogService,
    GetAgentVersionHandler,
    GetLatestPublishedAgentVersionHandler,
)
from hify.modules.agents.application.queries.list_agents import (
    ListAgentsForActorHandler,
    ListAgentsForActorQuery,
)
from hify.modules.agents.domain.entities import Agent, AgentVersion
from hify.modules.agents.domain.errors import (
    AgentAlreadyExistsError,
    AgentPermissionDeniedError,
    AgentValidationError,
)
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.knowledge.contracts.dto import KnowledgeBaseInfo
from hify.modules.providers.contracts.dto import ModelInfo
from hify.modules.workflows.contracts.dto import WorkflowVersionInfo
from hify.shared.domain.clock import Clock


class FixedClock(Clock):
    def now(self) -> datetime:
        return datetime(2026, 6, 22, tzinfo=UTC)


class FakeModelCatalog:
    def __init__(self, model: ModelInfo) -> None:
        self.model = model

    async def get_model(self, *, team_id: UUID, model_id: UUID) -> ModelInfo:
        assert team_id == self.model.team_id
        assert model_id == self.model.id
        return self.model

    async def list_models(self, *, team_id: UUID) -> tuple[ModelInfo, ...]:
        assert team_id == self.model.team_id
        return (self.model,)


class FakeKnowledgeBaseCatalog:
    def __init__(self) -> None:
        self.requests: list[tuple[UUID, UUID]] = []

    async def get_knowledge_base(
        self,
        *,
        team_id: UUID,
        knowledge_base_id: UUID,
    ) -> KnowledgeBaseInfo:
        self.requests.append((team_id, knowledge_base_id))
        return KnowledgeBaseInfo(
            id=knowledge_base_id,
            team_id=team_id,
            name="Team Docs",
            description=None,
            status="active",
            embedding_model_id=UUID("00000000-0000-7000-8000-000000000090"),
            embedding_dimensions=1536,
            document_count=1,
            chunk_count=3,
            created_at=datetime(2026, 6, 22, tzinfo=UTC),
            updated_at=datetime(2026, 6, 22, tzinfo=UTC),
        )


class FakeWorkflowCatalog:
    def __init__(self, workflow_version: WorkflowVersionInfo | None = None) -> None:
        self.workflow_version = workflow_version
        self.requests: list[tuple[UUID, UUID]] = []

    async def get_latest_published_version(
        self,
        *,
        team_id: UUID,
        workflow_id: UUID,
    ) -> WorkflowVersionInfo:
        self.requests.append((team_id, workflow_id))
        if self.workflow_version is None:
            raise AssertionError("workflow catalog should not be called")
        assert team_id == self.workflow_version.team_id
        assert workflow_id == self.workflow_version.workflow_id
        return self.workflow_version

    async def get_workflow_version(
        self,
        *,
        team_id: UUID,
        workflow_version_id: UUID,
    ) -> WorkflowVersionInfo:
        if self.workflow_version is None:
            raise AssertionError("workflow catalog should not be called")
        assert team_id == self.workflow_version.team_id
        assert workflow_version_id == self.workflow_version.id
        return self.workflow_version


class FakeAgentRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Agent] = {}

    async def add(self, agent: Agent) -> None:
        self.items[agent.id] = agent

    async def save(self, agent: Agent) -> None:
        self.items[agent.id] = agent

    async def get_by_id(self, agent_id: UUID) -> Agent | None:
        return self.items.get(agent_id)

    async def list_by_team(self, *, team_id: UUID) -> tuple[Agent, ...]:
        return tuple(agent for agent in self.items.values() if agent.team_id == team_id)

    async def get_by_team_and_name(self, *, team_id: UUID, name: str) -> Agent | None:
        for agent in self.items.values():
            if agent.team_id == team_id and agent.name.lower() == name.lower():
                return agent
        return None


class FakeAgentVersionRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, AgentVersion] = {}

    async def add(self, agent_version: AgentVersion) -> None:
        self.items[agent_version.id] = agent_version

    async def get_by_id(self, agent_version_id: UUID) -> AgentVersion | None:
        return self.items.get(agent_version_id)

    async def get_latest_by_agent_id(self, agent_id: UUID) -> AgentVersion | None:
        versions = [version for version in self.items.values() if version.agent_id == agent_id]
        if not versions:
            return None
        return max(versions, key=lambda version: version.version_number)


class FakeAgentsUnitOfWork:
    def __init__(self) -> None:
        self.agents = FakeAgentRepository()
        self.versions = FakeAgentVersionRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def actor_with_agent_permission() -> ActorContext:
    return ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="admin",
        permissions=("agents.manage",),
    )


def active_chat_model(team_id: UUID) -> ModelInfo:
    return ModelInfo(
        id=UUID("00000000-0000-7000-8000-000000000004"),
        team_id=team_id,
        provider_id=UUID("00000000-0000-7000-8000-000000000005"),
        provider_type="openai",
        provider_name="OpenAI",
        model_name="gpt-4.1",
        display_name="GPT 4.1",
        kind="chat",
        status="active",
        context_window_tokens=128000,
        supports_tools=True,
        supports_vision=True,
        supports_structured_output=True,
        price_per_1m_input_tokens=None,
        price_per_1m_output_tokens=None,
    )


def published_workflow_version(team_id: UUID) -> WorkflowVersionInfo:
    return WorkflowVersionInfo(
        id=UUID("00000000-0000-7000-8000-000000000011"),
        team_id=team_id,
        workflow_id=UUID("00000000-0000-7000-8000-000000000010"),
        version_number=3,
        name="Support Flow",
        description=None,
        definition={
            "nodes": [
                {"id": "start", "kind": "start", "config": {}},
                {"id": "end", "kind": "end", "config": {}},
            ],
            "edges": [{"source_node_id": "start", "target_node_id": "end"}],
        },
        created_at=datetime(2026, 6, 22, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_create_agent_validates_model_and_rejects_duplicate_name() -> None:
    unit_of_work = FakeAgentsUnitOfWork()
    actor = actor_with_agent_permission()
    handler = CreateAgentHandler(
        lambda: unit_of_work,
        FakeModelCatalog(active_chat_model(actor.team_id)),
        FakeKnowledgeBaseCatalog(),
        FixedClock(),
    )
    command = CreateAgentCommand(
        actor=actor,
        name="Support Bot",
        description="Answers questions",
        system_prompt="You are helpful.",
        provider_model_id=UUID("00000000-0000-7000-8000-000000000004"),
        knowledge_base_ids=(UUID("00000000-0000-7000-8000-000000000099"),),
    )

    agent = await handler.handle(command)

    assert agent.name == "Support Bot"
    assert agent.knowledge_base_ids == (UUID("00000000-0000-7000-8000-000000000099"),)
    assert unit_of_work.committed
    with pytest.raises(AgentAlreadyExistsError):
        await handler.handle(command)


@pytest.mark.asyncio
async def test_create_agent_requires_permission() -> None:
    unit_of_work = FakeAgentsUnitOfWork()
    actor = ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="viewer",
        permissions=(),
    )
    handler = CreateAgentHandler(
        lambda: unit_of_work,
        FakeModelCatalog(active_chat_model(actor.team_id)),
        FakeKnowledgeBaseCatalog(),
        FixedClock(),
    )

    with pytest.raises(AgentPermissionDeniedError):
        await handler.handle(
            CreateAgentCommand(
                actor=actor,
                name="Support Bot",
                description=None,
                system_prompt="You are helpful.",
                provider_model_id=UUID("00000000-0000-7000-8000-000000000004"),
            )
        )


@pytest.mark.asyncio
async def test_create_agent_rejects_non_chat_model() -> None:
    unit_of_work = FakeAgentsUnitOfWork()
    actor = actor_with_agent_permission()
    model = active_chat_model(actor.team_id)
    embedding_model = ModelInfo(
        id=model.id,
        team_id=model.team_id,
        provider_id=model.provider_id,
        provider_type=model.provider_type,
        provider_name=model.provider_name,
        model_name="text-embedding-3-large",
        display_name="Text Embedding 3 Large",
        kind="embedding",
        status="active",
        context_window_tokens=model.context_window_tokens,
        supports_tools=False,
        supports_vision=False,
        supports_structured_output=False,
        price_per_1m_input_tokens=None,
        price_per_1m_output_tokens=None,
    )
    handler = CreateAgentHandler(
        lambda: unit_of_work,
        FakeModelCatalog(embedding_model),
        FakeKnowledgeBaseCatalog(),
        FixedClock(),
    )

    with pytest.raises(AgentValidationError, match="chat"):
        await handler.handle(
            CreateAgentCommand(
                actor=actor,
                name="Support Bot",
                description=None,
                system_prompt="You are helpful.",
                provider_model_id=embedding_model.id,
            )
        )


@pytest.mark.asyncio
async def test_list_agents_returns_team_agents_and_requires_permission() -> None:
    unit_of_work = FakeAgentsUnitOfWork()
    actor = actor_with_agent_permission()
    model_catalog = FakeModelCatalog(active_chat_model(actor.team_id))
    agent = await CreateAgentHandler(
        lambda: unit_of_work,
        model_catalog,
        FakeKnowledgeBaseCatalog(),
        FixedClock(),
    ).handle(
        CreateAgentCommand(
            actor=actor,
            name="Support Bot",
            description=None,
            system_prompt="You are helpful.",
            provider_model_id=model_catalog.model.id,
        )
    )
    handler = ListAgentsForActorHandler(lambda: unit_of_work)

    listed = await handler.handle(ListAgentsForActorQuery(actor=actor))

    assert tuple(item.id for item in listed) == (agent.id,)
    viewer = ActorContext(
        user_id=actor.user_id,
        team_id=actor.team_id,
        membership_id=actor.membership_id,
        role="viewer",
        permissions=(),
    )
    with pytest.raises(AgentPermissionDeniedError):
        await handler.handle(ListAgentsForActorQuery(actor=viewer))


@pytest.mark.asyncio
async def test_publish_agent_creates_version_and_catalog_returns_it() -> None:
    unit_of_work = FakeAgentsUnitOfWork()
    actor = actor_with_agent_permission()
    model_catalog = FakeModelCatalog(active_chat_model(actor.team_id))
    knowledge_base_catalog = FakeKnowledgeBaseCatalog()
    knowledge_base_id = UUID("00000000-0000-7000-8000-000000000099")
    create_handler = CreateAgentHandler(
        lambda: unit_of_work,
        model_catalog,
        knowledge_base_catalog,
        FixedClock(),
    )
    agent = await create_handler.handle(
        CreateAgentCommand(
            actor=actor,
            name="Support Bot",
            description=None,
            system_prompt="You are helpful.",
            provider_model_id=model_catalog.model.id,
            knowledge_base_ids=(knowledge_base_id,),
        )
    )
    publish_handler = PublishAgentHandler(
        lambda: unit_of_work,
        model_catalog,
        knowledge_base_catalog,
        FakeWorkflowCatalog(),
        FixedClock(),
    )

    agent_version = await publish_handler.handle(
        PublishAgentCommand(actor=actor, agent_id=agent.id)
    )

    catalog = AgentCatalogService(
        GetAgentVersionHandler(lambda: unit_of_work),
        GetLatestPublishedAgentVersionHandler(lambda: unit_of_work),
    )
    latest = await catalog.get_latest_published_version(team_id=actor.team_id, agent_id=agent.id)
    fetched = await catalog.get_agent_version(
        team_id=actor.team_id,
        agent_version_id=agent_version.id,
    )
    persisted_agent = await unit_of_work.agents.get_by_id(agent.id)
    assert persisted_agent is not None
    assert persisted_agent.latest_version_number == 1
    assert agent_version.version_number == 1
    assert agent_version.knowledge_base_ids == (knowledge_base_id,)
    assert knowledge_base_catalog.requests == [
        (actor.team_id, knowledge_base_id),
        (actor.team_id, knowledge_base_id),
    ]
    assert latest == fetched == agent_version


@pytest.mark.asyncio
async def test_publish_agent_snapshots_bound_workflow_version() -> None:
    unit_of_work = FakeAgentsUnitOfWork()
    actor = actor_with_agent_permission()
    model_catalog = FakeModelCatalog(active_chat_model(actor.team_id))
    workflow_version = published_workflow_version(actor.team_id)
    workflow_catalog = FakeWorkflowCatalog(workflow_version)
    create_handler = CreateAgentHandler(
        lambda: unit_of_work,
        model_catalog,
        FakeKnowledgeBaseCatalog(),
        FixedClock(),
    )
    agent = await create_handler.handle(
        CreateAgentCommand(
            actor=actor,
            name="Support Bot",
            description=None,
            system_prompt="You are helpful.",
            provider_model_id=model_catalog.model.id,
            workflow_id=workflow_version.workflow_id,
        )
    )
    publish_handler = PublishAgentHandler(
        lambda: unit_of_work,
        model_catalog,
        FakeKnowledgeBaseCatalog(),
        workflow_catalog,
        FixedClock(),
    )

    agent_version = await publish_handler.handle(
        PublishAgentCommand(actor=actor, agent_id=agent.id)
    )

    assert agent.workflow_id == workflow_version.workflow_id
    assert agent_version.workflow_id == workflow_version.workflow_id
    assert agent_version.workflow_version_id == workflow_version.id
    assert agent_version.workflow_version_number == workflow_version.version_number
    assert agent_version.workflow_name == "Support Flow"
    assert agent_version.workflow_definition == workflow_version.definition
    assert workflow_catalog.requests == [(actor.team_id, workflow_version.workflow_id)]
