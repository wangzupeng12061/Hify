from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from uuid import UUID

from hify.modules.mcp.domain.value_objects import (
    McpServerStatus,
    McpToolStatus,
    McpTransport,
    normalize_endpoint_url,
    normalize_input_schema,
    normalize_server_description,
    normalize_server_name,
    normalize_tool_description,
    normalize_tool_name,
    parse_transport,
)
from hify.shared.domain.ids import new_uuid


@dataclass(slots=True)
class McpServer:
    id: UUID
    team_id: UUID
    name: str
    description: str | None
    transport: McpTransport
    endpoint_url: str
    status: McpServerStatus
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    last_discovered_at: datetime | None

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        name: str,
        description: str | None,
        transport: str,
        endpoint_url: str,
        created_by: UUID,
        now: datetime,
    ) -> McpServer:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            name=normalize_server_name(name),
            description=normalize_server_description(description),
            transport=parse_transport(transport),
            endpoint_url=normalize_endpoint_url(endpoint_url),
            status=McpServerStatus.ACTIVE,
            version=0,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            last_discovered_at=None,
        )

    def record_discovery(self, *, now: datetime) -> None:
        self.last_discovered_at = now
        self._mark_updated(now)

    def disable(self, *, now: datetime) -> None:
        if self.status is McpServerStatus.DISABLED:
            return
        self.status = McpServerStatus.DISABLED
        self._mark_updated(now)

    def _mark_updated(self, now: datetime) -> None:
        self.version += 1
        self.updated_at = now


@dataclass(slots=True)
class McpDiscoveredTool:
    id: UUID
    team_id: UUID
    server_id: UUID
    name: str
    description: str | None
    input_schema: Mapping[str, object]
    status: McpToolStatus
    version: int
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        server_id: UUID,
        name: str,
        description: str | None,
        input_schema: Mapping[str, object],
        now: datetime,
    ) -> McpDiscoveredTool:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            server_id=server_id,
            name=normalize_tool_name(name),
            description=normalize_tool_description(description),
            input_schema=normalize_input_schema(input_schema),
            status=McpToolStatus.ACTIVE,
            version=0,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )

    def update_from_discovery(
        self,
        *,
        description: str | None,
        input_schema: Mapping[str, object],
        now: datetime,
    ) -> None:
        self.description = normalize_tool_description(description)
        self.input_schema = normalize_input_schema(input_schema)
        self.status = McpToolStatus.ACTIVE
        self.last_seen_at = now
        self._mark_updated(now)

    def disable(self, *, now: datetime) -> None:
        if self.status is McpToolStatus.DISABLED:
            return
        self.status = McpToolStatus.DISABLED
        self._mark_updated(now)

    def _mark_updated(self, now: datetime) -> None:
        self.version += 1
        self.updated_at = now
