from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from hify.shared.domain.ids import new_uuid

from hify.modules.agents.domain.value_objects import (
    AgentStatus,
    ModelBindingSnapshot,
    normalize_agent_description,
    normalize_agent_name,
    normalize_system_prompt,
)


@dataclass(slots=True)
class Agent:
    id: UUID
    team_id: UUID
    name: str
    description: str | None
    system_prompt: str
    provider_model_id: UUID
    status: AgentStatus
    latest_version_number: int
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        name: str,
        description: str | None,
        system_prompt: str,
        provider_model_id: UUID,
        created_by: UUID,
        now: datetime,
    ) -> Agent:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            name=normalize_agent_name(name),
            description=normalize_agent_description(description),
            system_prompt=normalize_system_prompt(system_prompt),
            provider_model_id=provider_model_id,
            status=AgentStatus.DRAFT,
            latest_version_number=0,
            version=0,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

    def publish(
        self,
        *,
        model_snapshot: ModelBindingSnapshot,
        published_by: UUID,
        now: datetime,
    ) -> AgentVersion:
        next_version_number = self.latest_version_number + 1
        self.latest_version_number = next_version_number
        self.status = AgentStatus.PUBLISHED
        self._mark_updated(now)
        return AgentVersion.create(
            team_id=self.team_id,
            agent_id=self.id,
            version_number=next_version_number,
            name=self.name,
            description=self.description,
            system_prompt=self.system_prompt,
            model_snapshot=model_snapshot,
            published_by=published_by,
            now=now,
        )

    def _mark_updated(self, now: datetime) -> None:
        self.version += 1
        self.updated_at = now


@dataclass(slots=True)
class AgentVersion:
    id: UUID
    team_id: UUID
    agent_id: UUID
    version_number: int
    name: str
    description: str | None
    system_prompt: str
    provider_model_id: UUID
    provider_type: str
    provider_name: str
    model_name: str
    model_display_name: str
    context_window_tokens: int
    supports_tools: bool
    supports_vision: bool
    supports_structured_output: bool
    published_by: UUID
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        agent_id: UUID,
        version_number: int,
        name: str,
        description: str | None,
        system_prompt: str,
        model_snapshot: ModelBindingSnapshot,
        published_by: UUID,
        now: datetime,
    ) -> AgentVersion:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            agent_id=agent_id,
            version_number=version_number,
            name=normalize_agent_name(name),
            description=normalize_agent_description(description),
            system_prompt=normalize_system_prompt(system_prompt),
            provider_model_id=model_snapshot.provider_model_id,
            provider_type=model_snapshot.provider_type,
            provider_name=model_snapshot.provider_name,
            model_name=model_snapshot.model_name,
            model_display_name=model_snapshot.model_display_name,
            context_window_tokens=model_snapshot.context_window_tokens,
            supports_tools=model_snapshot.supports_tools,
            supports_vision=model_snapshot.supports_vision,
            supports_structured_output=model_snapshot.supports_structured_output,
            published_by=published_by,
            created_at=now,
        )
