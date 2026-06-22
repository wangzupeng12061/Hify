from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.agents.infrastructure.database.repositories import SqlAlchemyAgentRepository


class SessionSpy:
    def __init__(self) -> None:
        self.statement: Any | None = None

    async def scalar(self, statement: Any) -> None:
        self.statement = statement
        return None


def test_agent_name_lookup_matches_case_insensitive_unique_index() -> None:
    session = SessionSpy()
    repository = SqlAlchemyAgentRepository(cast(AsyncSession, session))

    _run(
        repository.get_by_team_and_name(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            name="Support Bot",
        ),
        session,
    )

    sql = _compile_sql(session.statement)
    params = session.statement.compile(dialect=postgresql.dialect()).params
    assert "lower(agents_agents.name)" in sql
    assert "support bot" in params.values()


def _run(awaitable: Any, session: SessionSpy) -> None:
    import asyncio

    asyncio.run(awaitable)
    assert session.statement is not None


def _compile_sql(statement: Any) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))
