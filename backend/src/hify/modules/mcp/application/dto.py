from __future__ import annotations

from hify.modules.mcp.contracts.dto import McpServerInfo, McpToolInfo
from hify.modules.mcp.domain.entities import McpDiscoveredTool, McpServer


def mcp_server_info_from_domain(server: McpServer) -> McpServerInfo:
    return McpServerInfo(
        id=server.id,
        team_id=server.team_id,
        name=server.name,
        description=server.description,
        transport=server.transport.value,
        endpoint_url=server.endpoint_url,
        status=server.status.value,
        created_at=server.created_at,
        updated_at=server.updated_at,
        last_discovered_at=server.last_discovered_at,
    )


def mcp_tool_info_from_domain(tool: McpDiscoveredTool) -> McpToolInfo:
    return McpToolInfo(
        id=tool.id,
        team_id=tool.team_id,
        server_id=tool.server_id,
        name=tool.name,
        description=tool.description,
        input_schema=dict(tool.input_schema),
        status=tool.status.value,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
        last_seen_at=tool.last_seen_at,
    )
