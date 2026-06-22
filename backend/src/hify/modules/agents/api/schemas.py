from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateAgentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    system_prompt: str = Field(min_length=1, max_length=20000)
    provider_model_id: UUID


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    name: str
    description: str | None
    status: str
    provider_model_id: UUID
    latest_version_number: int
    created_at: datetime
    updated_at: datetime


class AgentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
