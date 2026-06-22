from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from hify.modules.mcp.domain.entities import McpDiscoveredTool, McpServer
from hify.modules.mcp.domain.errors import McpValidationError
from hify.modules.mcp.domain.value_objects import McpServerStatus, McpToolStatus


NOW = datetime(2026, 6, 22, tzinfo=UTC)


def test_create_streamable_http_mcp_server() -> None:
    server = McpServer.create(
        team_id=UUID("00000000-0000-7000-8000-000000000001"),
        name=" Internal Docs ",
        description=" Team MCP ",
        transport="streamable_http",
        endpoint_url="https://mcp.example.com/mcp",
        created_by=UUID("00000000-0000-7000-8000-000000000002"),
        now=NOW,
    )

    assert server.name == "Internal Docs"
    assert server.description == "Team MCP"
    assert server.status is McpServerStatus.ACTIVE
    assert server.last_discovered_at is None


def test_mcp_server_rejects_non_https_endpoint() -> None:
    with pytest.raises(McpValidationError):
        McpServer.create(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            name="Internal Docs",
            description=None,
            transport="streamable_http",
            endpoint_url="http://mcp.example.com/mcp",
            created_by=UUID("00000000-0000-7000-8000-000000000002"),
            now=NOW,
        )


def test_discovered_tool_requires_object_schema() -> None:
    with pytest.raises(McpValidationError):
        McpDiscoveredTool.create(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            server_id=UUID("00000000-0000-7000-8000-000000000002"),
            name="search",
            description=None,
            input_schema={"type": "string"},
            now=NOW,
        )


def test_discovered_tool_update_marks_active_and_seen() -> None:
    tool = McpDiscoveredTool.create(
        team_id=UUID("00000000-0000-7000-8000-000000000001"),
        server_id=UUID("00000000-0000-7000-8000-000000000002"),
        name="search",
        description=None,
        input_schema={"type": "object"},
        now=NOW,
    )
    tool.disable(now=NOW)

    tool.update_from_discovery(
        description="Search docs",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        now=NOW,
    )

    assert tool.status is McpToolStatus.ACTIVE
    assert tool.description == "Search docs"
    assert tool.version == 2
