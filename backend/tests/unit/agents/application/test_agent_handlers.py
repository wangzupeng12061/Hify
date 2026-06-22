from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from hify.modules.agents.application.commands.create_agent import CreateAgentCommand, CreateAgentHandler
from hify.modules.agents.application.commands.publish_agent import PublishAgentCommand, PublishAgentHandler
from hify.modules.agents.application.queries.get_agent_version import (
    AgentCatalogService,
    GetAgentVersionHandler,
    GetLatestPublishedAgentVersionHandler,
)
from hify.modules.agents.domain.entities import Agent, AgentVersion
from hify.modules.agents.domain.errors import (
    AgentAlreadyExistsError,
    AgentPermissionDeniedError,
    AgentValidationError,
)
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.providers.contracts.dto import ModelInfo
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


class FakeAgentRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Agent] = {}

    async def add(self, agent: Agent) -> None:
        self.items[agent.id] = agent

    async def save(self, agent: Agent) -> None:
        self.items[agent.id] = agent

    async def get_by_id(self, agent_id: UUID) -> Agent | None:
        return self.items.get(agent_id)

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
    )


@pytest.mark.asyncio
async def test_create_agent_validates_model_and_rejects_duplicate_name() -> None:
    unit_of_work = FakeAgentsUnitOfWork()
    actor = actor_with_agent_permission()
    handler = CreateAgentHandler(
        lambda: unit_of_work,
        FakeModelCatalog(active_chat_model(actor.team_id)),
        FixedClock(),
    )
    command = CreateAgentCommand(
        actor=actor,
        name="Support Bot",
        description="Answers questions",
        system_prompt="You are helpful.",
        provider_model_id=UUID("00000000-0000-7000-8000-000000000004"),
    )

    agent = await handler.handle(command)

    assert agent.name == "Support Bot"
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
    )
    handler = CreateAgentHandler(lambda: unit_of_work, FakeModelCatalog(embedding_model), FixedClock())

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
async def test_publish_agent_creates_version_and_catalog_returns_it() -> None:
    unit_of_work = FakeAgentsUnitOfWork()
    actor = actor_with_agent_permission()
    model_catalog = FakeModelCatalog(active_chat_model(actor.team_id))
    create_handler = CreateAgentHandler(lambda: unit_of_work, model_catalog, FixedClock())
    agent = await create_handler.handle(
        CreateAgentCommand(
            actor=actor,
            name="Support Bot",
            description=None,
            system_prompt="You are helpful.",
            provider_model_id=model_catalog.model.id,
        )
    )
    publish_handler = PublishAgentHandler(lambda: unit_of_work, model_catalog, FixedClock())

    agent_version = await publish_handler.handle(PublishAgentCommand(actor=actor, agent_id=agent.id))

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
    assert latest == fetched == agent_version
