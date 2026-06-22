from __future__ import annotations

from datetime import datetime
from typing import Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateToolRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    tool_kind: str = Field(pattern="^(builtin|http)$")
    input_schema: Mapping[str, object]
    builtin_name: str | None = Field(default=None, max_length=160)
    endpoint_url: str | None = Field(default=None, max_length=1000)
    http_method: str | None = Field(default=None, pattern="^(GET|POST|PUT|PATCH|DELETE)$")
    http_headers: Mapping[str, str] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    name: str
    description: str | None
    tool_kind: str
    status: str
    input_schema: Mapping[str, object]
    builtin_name: str | None
    endpoint_url: str | None
    http_method: str | None
    http_headers: Mapping[str, str]
    created_at: datetime
    updated_at: datetime
