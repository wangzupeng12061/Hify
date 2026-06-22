from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ToolInfo:
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


@dataclass(frozen=True, slots=True)
class ToolExecutionRequest:
    team_id: UUID
    tool_id: UUID
    tool_call_id: UUID
    arguments: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    tool_call_id: UUID
    content: str
    metadata: Mapping[str, object]
