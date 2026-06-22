from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from uuid import UUID


@dataclass(frozen=True, slots=True)
class McpServerInfo:
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


@dataclass(frozen=True, slots=True)
class McpToolInfo:
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


@dataclass(frozen=True, slots=True)
class DiscoveredMcpTool:
    name: str
    description: str | None
    input_schema: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class McpToolInvocationRequest:
    team_id: UUID
    server_id: UUID
    tool_id: UUID
    tool_call_id: UUID
    arguments: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class McpToolInvocationResult:
    tool_call_id: UUID
    content: str
    metadata: Mapping[str, object]
