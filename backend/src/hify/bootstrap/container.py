from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from hify.bootstrap.settings import Settings
from hify.modules.agents.wiring import AgentsModule, create_agents_module
from hify.modules.conversations.wiring import ConversationsModule, create_conversations_module
from hify.modules.identity.wiring import IdentityModule, create_identity_module
from hify.modules.providers.wiring import ProvidersModule, create_providers_module
from hify.modules.runs.wiring import RunsModule, create_runs_module
from hify.shared.infrastructure.database import create_engine, create_session_factory


@dataclass(frozen=True, slots=True)
class HifyContainer:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    identity: IdentityModule
    providers: ProvidersModule
    agents: AgentsModule
    conversations: ConversationsModule
    runs: RunsModule


def create_container(settings: Settings | None = None) -> HifyContainer:
    resolved_settings = settings or Settings()
    engine = create_engine(
        resolved_settings.database_url,
        echo=resolved_settings.database_echo,
    )
    session_factory = create_session_factory(engine)
    identity = create_identity_module(session_factory)
    providers = create_providers_module(
        session_factory,
        credential_encryption_key=resolved_settings.provider_credential_encryption_key,
        credential_key_version=resolved_settings.provider_credential_key_version,
    )
    agents = create_agents_module(session_factory, model_catalog=providers.model_catalog)
    conversations = create_conversations_module(
        session_factory,
        agent_catalog=agents.agent_catalog,
    )
    runs = create_runs_module(
        session_factory,
        conversation_reader=conversations.conversation_reader,
        agent_catalog=agents.agent_catalog,
        model_gateway=providers.model_gateway,
    )
    return HifyContainer(
        settings=resolved_settings,
        engine=engine,
        session_factory=session_factory,
        identity=identity,
        providers=providers,
        agents=agents,
        conversations=conversations,
        runs=runs,
    )
