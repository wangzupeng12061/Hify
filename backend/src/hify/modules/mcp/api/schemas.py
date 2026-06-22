from __future__ import annotations

from datetime import datetime
from typing import Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateMcpServerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    transport: str = Field(pattern="^streamable_http$")
    endpoint_url: str = Field(min_length=1, max_length=1000)


class McpServerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    name: str
    description: str | None
    transport: str
    endpoint_url: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_discovered_at: datetime | None


class McpToolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    server_id: UUID
    name: str
    description: str | None
    input_schema: Mapping[str, object]
    status: str
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime
