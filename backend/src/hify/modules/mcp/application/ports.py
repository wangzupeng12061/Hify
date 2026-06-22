from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Self

from hify.modules.mcp.contracts.dto import (
    DiscoveredMcpTool,
    McpToolInvocationRequest,
    McpToolInvocationResult,
)
from hify.modules.mcp.domain.entities import McpServer
from hify.modules.mcp.domain.repositories import McpServerRepository, McpToolRepository
from hify.shared.application.uow import UnitOfWork


class McpUnitOfWork(UnitOfWork, Protocol):
    servers: McpServerRepository
    tools: McpToolRepository

    async def __aenter__(self) -> Self: ...


McpUnitOfWorkFactory = Callable[[], McpUnitOfWork]


class McpClient(Protocol):
    async def list_tools(self, server: McpServer) -> tuple[DiscoveredMcpTool, ...]: ...

    async def call_tool(
        self,
        server: McpServer,
        tool_name: str,
        request: McpToolInvocationRequest,
    ) -> McpToolInvocationResult: ...
