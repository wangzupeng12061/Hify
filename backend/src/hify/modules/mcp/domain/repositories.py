from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.mcp.domain.entities import McpDiscoveredTool, McpServer


class McpServerRepository(Protocol):
    async def add(self, server: McpServer) -> None: ...

    async def save(self, server: McpServer) -> None: ...

    async def get_by_id(self, server_id: UUID) -> McpServer | None: ...

    async def get_by_team_and_name(self, *, team_id: UUID, name: str) -> McpServer | None: ...

    async def list_by_team(self, team_id: UUID) -> tuple[McpServer, ...]: ...


class McpToolRepository(Protocol):
    async def add(self, tool: McpDiscoveredTool) -> None: ...

    async def save(self, tool: McpDiscoveredTool) -> None: ...

    async def get_by_id(self, tool_id: UUID) -> McpDiscoveredTool | None: ...

    async def get_by_server_and_name(
        self,
        *,
        server_id: UUID,
        name: str,
    ) -> McpDiscoveredTool | None: ...

    async def list_by_server(self, *, team_id: UUID, server_id: UUID) -> tuple[McpDiscoveredTool, ...]: ...
