from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from hify.modules.tools.domain.entities import ToolDefinition
from hify.modules.tools.domain.errors import ToolValidationError
from hify.modules.tools.domain.value_objects import HttpToolMethod, ToolKind, ToolStatus


def test_create_builtin_tool_definition() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)

    tool = ToolDefinition.create(
        team_id=UUID("00000000-0000-7000-8000-000000000001"),
        name="Web Search",
        description=" Search public docs ",
        tool_kind=ToolKind.BUILTIN,
        input_schema={"type": "object", "properties": {}},
        builtin_name="web.search",
        endpoint_url=None,
        http_method=None,
        http_headers=None,
        created_by=UUID("00000000-0000-7000-8000-000000000002"),
        now=now,
    )

    assert tool.name == "Web Search"
    assert tool.description == "Search public docs"
    assert tool.status is ToolStatus.ACTIVE
    assert tool.builtin_name == "web.search"
    assert tool.http_headers == {}


def test_create_http_tool_requires_endpoint_and_method() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)

    with pytest.raises(ToolValidationError):
        ToolDefinition.create(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            name="Lookup",
            description=None,
            tool_kind=ToolKind.HTTP,
            input_schema={"type": "object"},
            builtin_name=None,
            endpoint_url=None,
            http_method=HttpToolMethod.POST,
            http_headers={},
            created_by=UUID("00000000-0000-7000-8000-000000000002"),
            now=now,
        )


def test_input_schema_must_be_object_schema() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)

    with pytest.raises(ToolValidationError):
        ToolDefinition.create(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            name="Lookup",
            description=None,
            tool_kind=ToolKind.BUILTIN,
            input_schema={"type": "string"},
            builtin_name="lookup",
            endpoint_url=None,
            http_method=None,
            http_headers={},
            created_by=UUID("00000000-0000-7000-8000-000000000002"),
            now=now,
        )
