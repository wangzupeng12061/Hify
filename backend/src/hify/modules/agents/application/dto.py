from __future__ import annotations

from hify.modules.agents.contracts.dto import AgentInfo, AgentVersionInfo
from hify.modules.agents.domain.entities import Agent, AgentVersion


def agent_info_from_domain(agent: Agent) -> AgentInfo:
    return AgentInfo(
        id=agent.id,
        team_id=agent.team_id,
        name=agent.name,
        description=agent.description,
        status=agent.status.value,
        provider_model_id=agent.provider_model_id,
        knowledge_base_ids=agent.knowledge_base_ids,
        latest_version_number=agent.latest_version_number,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


def agent_version_info_from_domain(agent_version: AgentVersion) -> AgentVersionInfo:
    return AgentVersionInfo(
        id=agent_version.id,
        team_id=agent_version.team_id,
        agent_id=agent_version.agent_id,
        version_number=agent_version.version_number,
        name=agent_version.name,
        description=agent_version.description,
        system_prompt=agent_version.system_prompt,
        knowledge_base_ids=agent_version.knowledge_base_ids,
        provider_model_id=agent_version.provider_model_id,
        provider_type=agent_version.provider_type,
        provider_name=agent_version.provider_name,
        model_name=agent_version.model_name,
        model_display_name=agent_version.model_display_name,
        context_window_tokens=agent_version.context_window_tokens,
        supports_tools=agent_version.supports_tools,
        supports_vision=agent_version.supports_vision,
        supports_structured_output=agent_version.supports_structured_output,
        created_at=agent_version.created_at,
    )
