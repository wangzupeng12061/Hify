from __future__ import annotations

from hify.modules.mcp.application.ports import McpClient
from hify.modules.mcp.contracts.dto import (
    DiscoveredMcpTool,
    McpToolInvocationRequest,
    McpToolInvocationResult,
)
from hify.modules.mcp.domain.entities import McpServer
from hify.modules.mcp.domain.errors import McpClientNotConfiguredError


class UnavailableMcpClient(McpClient):
    async def list_tools(self, server: McpServer) -> tuple[DiscoveredMcpTool, ...]:
        raise McpClientNotConfiguredError(
            "mcp client is not configured",
            metadata={"server_id": str(server.id)},
        )

    async def call_tool(
        self,
        server: McpServer,
        tool_name: str,
        request: McpToolInvocationRequest,
    ) -> McpToolInvocationResult:
        _ = tool_name, request
        raise McpClientNotConfiguredError(
            "mcp client is not configured",
            metadata={"server_id": str(server.id)},
        )
