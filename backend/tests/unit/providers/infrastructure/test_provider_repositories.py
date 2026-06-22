from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.providers.domain.value_objects import ProviderType
from hify.modules.providers.infrastructure.database.repositories import (
    SqlAlchemyModelProviderRepository,
    SqlAlchemyProviderModelRepository,
)


class SessionSpy:
    def __init__(self) -> None:
        self.statement: Any | None = None

    async def scalar(self, statement: Any) -> None:
        self.statement = statement
        return None


def test_provider_name_lookup_matches_case_insensitive_unique_index() -> None:
    session = SessionSpy()
    repository = SqlAlchemyModelProviderRepository(cast(AsyncSession, session))

    _run(
        repository.get_by_team_type_and_name(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            provider_type=ProviderType.OPENAI,
            name="OpenAI",
        ),
        session,
    )

    sql = _compile_sql(session.statement)
    params = session.statement.compile(dialect=postgresql.dialect()).params
    assert "lower(providers_providers.name)" in sql
    assert "openai" in params.values()


def test_model_name_lookup_matches_case_insensitive_unique_index() -> None:
    session = SessionSpy()
    repository = SqlAlchemyProviderModelRepository(cast(AsyncSession, session))

    _run(
        repository.get_by_provider_and_name(
            provider_id=UUID("00000000-0000-7000-8000-000000000001"),
            model_name="GPT-4.1",
        ),
        session,
    )

    sql = _compile_sql(session.statement)
    params = session.statement.compile(dialect=postgresql.dialect()).params
    assert "lower(providers_models.model_name)" in sql
    assert "gpt-4.1" in params.values()


def _run(awaitable: Any, session: SessionSpy) -> None:
    import asyncio

    asyncio.run(awaitable)
    assert session.statement is not None


def _compile_sql(statement: Any) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))
