from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.runs.infrastructure.database.repositories import SqlAlchemyRunEventRepository


class SessionSpy:
    def __init__(self) -> None:
        self.statement: Any | None = None

    async def scalars(self, statement: Any) -> "ScalarResultSpy":
        self.statement = statement
        return ScalarResultSpy()


class ScalarResultSpy:
    def all(self) -> list[Any]:
        return []


def test_run_event_list_uses_sequence_cursor_order() -> None:
    session = SessionSpy()
    repository = SqlAlchemyRunEventRepository(cast(AsyncSession, session))

    _run(
        repository.list_by_run(
            run_id=UUID("00000000-0000-7000-8000-000000000001"),
            after_sequence_number=7,
            limit=21,
        ),
        session,
    )

    sql = _compile_sql(session.statement)
    assert "runs_events.sequence_number >" in sql
    assert "ORDER BY runs_events.sequence_number ASC" in sql
    assert "LIMIT" in sql


def _run(awaitable: Any, session: SessionSpy) -> None:
    import asyncio

    asyncio.run(awaitable)
    assert session.statement is not None


def _compile_sql(statement: Any) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))
