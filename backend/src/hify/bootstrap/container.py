from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from hify.bootstrap.settings import Settings
from hify.modules.agents.wiring import AgentsModule, create_agents_module
from hify.modules.conversations.wiring import ConversationsModule, create_conversations_module
from hify.modules.identity.wiring import IdentityModule, create_identity_module
from hify.modules.jobs.wiring import JobsModule, create_jobs_module
from hify.modules.knowledge.wiring import KnowledgeModule, create_knowledge_module
from hify.modules.mcp.wiring import McpModule, create_mcp_module
from hify.modules.providers.wiring import ProvidersModule, create_providers_module
from hify.modules.runs.wiring import RunsModule, create_runs_module
from hify.modules.tools.wiring import ToolsModule, create_tools_module
from hify.modules.usage.wiring import UsageModule, create_usage_module
from hify.modules.workflows.wiring import WorkflowsModule, create_workflows_module
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
    jobs: JobsModule
    knowledge: KnowledgeModule
    mcp: McpModule
    runs: RunsModule
    tools: ToolsModule
    usage: UsageModule
    workflows: WorkflowsModule


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
    jobs = create_jobs_module(session_factory)
    knowledge = create_knowledge_module(
        session_factory,
        model_catalog=providers.model_catalog,
        embedding_gateway=providers.embedding_gateway,
    )
    mcp = create_mcp_module(session_factory)
    tools = create_tools_module(
        session_factory,
        mcp_tool_discovery=mcp.mcp_tool_discovery,
        mcp_tool_invoker=mcp.mcp_tool_invoker,
    )
    workflows = create_workflows_module(
        session_factory,
        model_catalog=providers.model_catalog,
        tool_catalog=tools.tool_catalog,
    )
    agents = create_agents_module(
        session_factory,
        model_catalog=providers.model_catalog,
        knowledge_base_catalog=knowledge.knowledge_base_catalog,
        workflow_catalog=workflows.workflow_catalog,
    )
    conversations = create_conversations_module(
        session_factory,
        agent_catalog=agents.agent_catalog,
    )
    usage = create_usage_module(session_factory)
    runs = create_runs_module(
        session_factory,
        conversation_reader=conversations.conversation_reader,
        conversation_writer=conversations.conversation_writer,
        agent_catalog=agents.agent_catalog,
        model_gateway=providers.model_gateway,
        tool_executor=tools.tool_executor,
        knowledge_retriever=knowledge.knowledge_retriever,
        usage_recorder=usage.usage_recorder,
        usage_quota_checker=usage.usage_quota_checker,
    )
    return HifyContainer(
        settings=resolved_settings,
        engine=engine,
        session_factory=session_factory,
        identity=identity,
        providers=providers,
        agents=agents,
        conversations=conversations,
        jobs=jobs,
        knowledge=knowledge,
        mcp=mcp,
        runs=runs,
        tools=tools,
        usage=usage,
        workflows=workflows,
    )
