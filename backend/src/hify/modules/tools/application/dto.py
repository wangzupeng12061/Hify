from __future__ import annotations

from hify.modules.tools.contracts.dto import ToolInfo
from hify.modules.tools.domain.entities import ToolDefinition


def tool_info_from_domain(tool: ToolDefinition) -> ToolInfo:
    return ToolInfo(
        id=tool.id,
        team_id=tool.team_id,
        name=tool.name,
        description=tool.description,
        tool_kind=tool.tool_kind.value,
        status=tool.status.value,
        input_schema=tool.input_schema,
        builtin_name=tool.builtin_name,
        endpoint_url=tool.endpoint_url,
        http_method=tool.http_method.value if tool.http_method is not None else None,
        http_headers=tool.http_headers,
        mcp_server_id=tool.mcp_server_id,
        mcp_tool_id=tool.mcp_tool_id,
        mcp_tool_name=tool.mcp_tool_name,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
    )
