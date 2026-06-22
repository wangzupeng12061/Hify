from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AgentInfo:
    id: UUID
    team_id: UUID
    name: str
    description: str | None
    status: str
    provider_model_id: UUID
    latest_version_number: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AgentVersionInfo:
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
    created_at: datetime
