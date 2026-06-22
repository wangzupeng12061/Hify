from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.mcp.infrastructure.database.models import McpDiscoveredToolModel, McpServerModel
from hify.modules.mcp.infrastructure.database.repositories import (
    SqlAlchemyMcpServerRepository,
    SqlAlchemyMcpToolRepository,
)


class SessionSpy:
    def __init__(self) -> None:
        self.statement: Any | None = None

    async def scalar(self, statement: Any) -> None:
        self.statement = statement
        return None

    async def scalars(self, statement: Any) -> tuple[Any, ...]:
        self.statement = statement
        return ()


def test_mcp_server_name_lookup_matches_case_insensitive_unique_index() -> None:
    session = SessionSpy()
    repository = SqlAlchemyMcpServerRepository(cast(AsyncSession, session))

    _run(
        repository.get_by_team_and_name(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            name="Docs",
        ),
        session,
    )

    sql = _compile_sql(session.statement)
    params = session.statement.compile(dialect=postgresql.dialect()).params
    assert "lower(mcp_servers.name)" in sql
    assert "docs" in params.values()


def test_mcp_tool_list_filters_by_team_and_server() -> None:
    session = SessionSpy()
    repository = SqlAlchemyMcpToolRepository(cast(AsyncSession, session))

    _run(
        repository.list_by_server(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            server_id=UUID("00000000-0000-7000-8000-000000000002"),
        ),
        session,
    )

    sql = _compile_sql(session.statement)
    assert "mcp_discovered_tools.team_id" in sql
    assert "mcp_discovered_tools.server_id" in sql
    assert "ORDER BY mcp_discovered_tools.name" in sql


def test_mcp_models_have_expected_indexes() -> None:
    server_index_names = {index.name for index in McpServerModel.__table__.indexes}
    tool_index_names = {index.name for index in McpDiscoveredToolModel.__table__.indexes}

    assert "uq_mcp_servers__team_name_lower" in server_index_names
    assert "ix_mcp_servers__team_status_created_id" in server_index_names
    assert "uq_mcp_discovered_tools__server_name" in tool_index_names
    assert "ix_mcp_discovered_tools__team_server_status_name" in tool_index_names


def _run(awaitable: Any, session: SessionSpy) -> None:
    import asyncio

    asyncio.run(awaitable)
    assert session.statement is not None


def _compile_sql(statement: Any) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))
