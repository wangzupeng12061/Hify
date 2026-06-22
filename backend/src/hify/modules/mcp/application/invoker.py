from __future__ import annotations

from hify.modules.mcp.application.ports import McpClient, McpUnitOfWorkFactory
from hify.modules.mcp.contracts.dto import McpToolInvocationRequest, McpToolInvocationResult
from hify.modules.mcp.contracts.services import McpToolInvoker
from hify.modules.mcp.domain.errors import McpServerNotFoundError, McpToolNotFoundError
from hify.modules.mcp.domain.value_objects import McpServerStatus, McpToolStatus


class McpToolInvokerService(McpToolInvoker):
    def __init__(self, unit_of_work_factory: McpUnitOfWorkFactory, mcp_client: McpClient) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._mcp_client = mcp_client

    async def invoke_tool(self, request: McpToolInvocationRequest) -> McpToolInvocationResult:
        async with self._unit_of_work_factory() as unit_of_work:
            server = await unit_of_work.servers.get_by_id(request.server_id)
            tool = await unit_of_work.tools.get_by_id(request.tool_id)
        if server is None or server.team_id != request.team_id:
            raise McpServerNotFoundError("mcp server was not found")
        if server.status is not McpServerStatus.ACTIVE:
            raise McpServerNotFoundError("mcp server was not found")
        if tool is None or tool.team_id != request.team_id or tool.server_id != server.id:
            raise McpToolNotFoundError("mcp tool was not found")
        if tool.status is not McpToolStatus.ACTIVE:
            raise McpToolNotFoundError("mcp tool was not found")
        return await self._mcp_client.call_tool(server, tool.name, request)
