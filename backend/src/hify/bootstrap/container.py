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
    identity = create_identity_module(
        session_factory,
        auth_cookie_name=resolved_settings.auth_cookie_name,
        auth_cookie_secure=resolved_settings.auth_cookie_secure,
        auth_cookie_samesite=resolved_settings.auth_cookie_samesite,
        auth_session_ttl_seconds=resolved_settings.auth_session_ttl_seconds,
        auth_dev_login_enabled=resolved_settings.auth_dev_login_enabled,
        auth_oidc_enabled=resolved_settings.auth_oidc_enabled,
        auth_bootstrap_token=resolved_settings.auth_bootstrap_token,
        auth_trusted_header_enabled=resolved_settings.auth_trusted_header_enabled,
        auth_trusted_email_header=resolved_settings.auth_trusted_email_header,
        auth_trusted_display_name_header=resolved_settings.auth_trusted_display_name_header,
        auth_trusted_team_name=resolved_settings.auth_trusted_team_name,
        auth_trusted_default_role=resolved_settings.auth_trusted_default_role,
    )
    providers = create_providers_module(
        session_factory,
        credential_encryption_key=resolved_settings.provider_credential_encryption_key,
        credential_key_version=resolved_settings.provider_credential_key_version,
        request_authenticator=identity.request_authenticator,
    )
    jobs = create_jobs_module(
        session_factory,
        request_authenticator=identity.request_authenticator,
    )
    knowledge = create_knowledge_module(
        session_factory,
        model_catalog=providers.model_catalog,
        embedding_gateway=providers.embedding_gateway,
        request_authenticator=identity.request_authenticator,
    )
    mcp = create_mcp_module(
        session_factory,
        request_authenticator=identity.request_authenticator,
    )
    tools = create_tools_module(
        session_factory,
        mcp_tool_discovery=mcp.mcp_tool_discovery,
        mcp_tool_invoker=mcp.mcp_tool_invoker,
        request_authenticator=identity.request_authenticator,
    )
    workflows = create_workflows_module(
        session_factory,
        model_catalog=providers.model_catalog,
        tool_catalog=tools.tool_catalog,
        request_authenticator=identity.request_authenticator,
    )
    agents = create_agents_module(
        session_factory,
        model_catalog=providers.model_catalog,
        knowledge_base_catalog=knowledge.knowledge_base_catalog,
        workflow_catalog=workflows.workflow_catalog,
        request_authenticator=identity.request_authenticator,
    )
    conversations = create_conversations_module(
        session_factory,
        agent_catalog=agents.agent_catalog,
        request_authenticator=identity.request_authenticator,
    )
    usage = create_usage_module(
        session_factory,
        model_pricing_catalog=providers.model_pricing_catalog,
        request_authenticator=identity.request_authenticator,
    )
    runs = create_runs_module(
        session_factory,
        conversation_reader=conversations.conversation_reader,
        conversation_writer=conversations.conversation_writer,
        agent_catalog=agents.agent_catalog,
        model_gateway=providers.model_gateway,
        tool_executor=tools.tool_executor,
        knowledge_retriever=knowledge.knowledge_retriever,
        usage_recorder=usage.usage_recorder,
        usage_reader=usage.usage_reader,
        usage_quota_checker=usage.usage_quota_checker,
        request_authenticator=identity.request_authenticator,
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
