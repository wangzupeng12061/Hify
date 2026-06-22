from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.knowledge.infrastructure.database.repositories import (
    SqlAlchemyKnowledgeBaseRepository,
    SqlAlchemyKnowledgeChunkRepository,
)


class SessionSpy:
    def __init__(self) -> None:
        self.statement: Any | None = None

    async def scalar(self, statement: Any) -> None:
        self.statement = statement
        return None

    async def execute(self, statement: Any) -> Any:
        self.statement = statement
        return _Rows()


class _Rows:
    def all(self) -> list[Any]:
        return []


def test_knowledge_base_name_lookup_matches_case_insensitive_unique_index() -> None:
    session = SessionSpy()
    repository = SqlAlchemyKnowledgeBaseRepository(cast(AsyncSession, session))

    _run(
        repository.get_by_team_and_name(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            name="Team Docs",
        ),
        session,
    )

    sql = _compile_sql(session.statement)
    params = session.statement.compile(dialect=postgresql.dialect()).params
    assert "lower(knowledge_bases.name)" in sql
    assert "team docs" in params.values()


def test_chunk_similarity_search_limits_team_and_knowledge_base() -> None:
    session = SessionSpy()
    repository = SqlAlchemyKnowledgeChunkRepository(cast(AsyncSession, session))

    _run(
        repository.search_similar(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            knowledge_base_ids=(UUID("00000000-0000-7000-8000-000000000002"),),
            query_embedding=tuple(0.001 for _ in range(1536)),
            limit=5,
        ),
        session,
    )

    sql = _compile_sql(session.statement)
    assert "knowledge_chunks.team_id" in sql
    assert "knowledge_chunks.knowledge_base_id IN" in sql
    assert "ORDER BY distance" in sql
    assert "LIMIT" in sql


def _run(awaitable: Any, session: SessionSpy) -> None:
    import asyncio

    asyncio.run(awaitable)
    assert session.statement is not None


def _compile_sql(statement: Any) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))
