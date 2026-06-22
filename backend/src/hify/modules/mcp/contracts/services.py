from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.mcp.contracts.dto import (
    McpServerInfo,
    McpToolInfo,
    McpToolInvocationRequest,
    McpToolInvocationResult,
)


class McpServerCatalog(Protocol):
    async def get_server(self, *, team_id: UUID, server_id: UUID) -> McpServerInfo: ...

    async def list_servers(self, *, team_id: UUID) -> tuple[McpServerInfo, ...]: ...


class McpToolDiscovery(Protocol):
    async def get_tool(self, *, team_id: UUID, tool_id: UUID) -> McpToolInfo: ...

    async def list_tools(self, *, team_id: UUID, server_id: UUID) -> tuple[McpToolInfo, ...]: ...

    async def refresh_tools(self, *, team_id: UUID, server_id: UUID) -> tuple[McpToolInfo, ...]: ...


class McpToolInvoker(Protocol):
    async def invoke_tool(self, request: McpToolInvocationRequest) -> McpToolInvocationResult: ...
