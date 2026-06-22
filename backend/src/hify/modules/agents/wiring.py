from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.agents.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.agents.api.router import create_agents_router
from hify.modules.agents.application.commands.create_agent import CreateAgentHandler
from hify.modules.agents.application.commands.publish_agent import PublishAgentHandler
from hify.modules.agents.application.queries.get_agent_version import (
    AgentCatalogService,
    GetAgentVersionHandler,
    GetLatestPublishedAgentVersionHandler,
)
from hify.modules.agents.contracts.services import AgentCatalog
from hify.modules.agents.infrastructure.database.uow import SqlAlchemyAgentsUnitOfWork
from hify.modules.knowledge.contracts.services import KnowledgeBaseCatalog
from hify.modules.providers.contracts.services import ModelCatalog
from hify.shared.domain.clock import Clock, SystemClock


@dataclass(frozen=True, slots=True)
class AgentsModule:
    router: APIRouter
    agent_catalog: AgentCatalog


def create_agents_module(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    model_catalog: ModelCatalog,
    knowledge_base_catalog: KnowledgeBaseCatalog,
    clock: Clock | None = None,
) -> AgentsModule:
    module_clock = clock or SystemClock()

    def unit_of_work_factory() -> SqlAlchemyAgentsUnitOfWork:
        return SqlAlchemyAgentsUnitOfWork(session_factory)

    create_agent_handler = CreateAgentHandler(
        unit_of_work_factory,
        model_catalog,
        knowledge_base_catalog,
        module_clock,
    )
    publish_agent_handler = PublishAgentHandler(
        unit_of_work_factory,
        model_catalog,
        knowledge_base_catalog,
        module_clock,
    )
    get_agent_version_handler = GetAgentVersionHandler(unit_of_work_factory)
    get_latest_published_agent_version_handler = GetLatestPublishedAgentVersionHandler(
        unit_of_work_factory
    )
    agent_catalog = AgentCatalogService(
        get_agent_version_handler,
        get_latest_published_agent_version_handler,
    )
    router = create_agents_router(
        create_agent_handler=create_agent_handler,
        publish_agent_handler=publish_agent_handler,
        request_authenticator=AuthenticationNotConfiguredAuthenticator(),
    )
    return AgentsModule(router=router, agent_catalog=agent_catalog)
