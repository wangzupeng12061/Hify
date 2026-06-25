from __future__ import annotations

from typing import Any, cast

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.identity.domain.value_objects import EmailAddress
from hify.modules.identity.infrastructure.database.repositories import (
    SqlAlchemyMembershipRepository,
    SqlAlchemyTeamRepository,
    SqlAlchemyUserRepository,
)


class SessionSpy:
    def __init__(self) -> None:
        self.statement: Any | None = None

    async def scalar(self, statement: Any) -> None:
        self.statement = statement
        return None


def test_user_lookup_matches_case_insensitive_unique_index() -> None:
    session = SessionSpy()
    repository = SqlAlchemyUserRepository(cast(AsyncSession, session))

    email = EmailAddress.parse("OWNER@Example.COM")
    statement = _run(repository.get_by_email(email), session)

    sql = _compile_sql(statement)
    assert "lower(identity_users.email)" in sql
    assert statement.compile(dialect=postgresql.dialect()).params["lower_1"] == "owner@example.com"


def test_team_lookup_matches_case_insensitive_unique_index() -> None:
    session = SessionSpy()
    repository = SqlAlchemyTeamRepository(cast(AsyncSession, session))

    statement = _run(repository.get_by_name("Platform"), session)

    sql = _compile_sql(statement)
    assert "lower(identity_teams.name)" in sql
    assert statement.compile(dialect=postgresql.dialect()).params["lower_1"] == "platform"


def test_active_owner_lookup_stays_inside_identity_memberships() -> None:
    session = SessionSpy()
    repository = SqlAlchemyMembershipRepository(cast(AsyncSession, session))

    statement = _run(repository.has_active_owner(), session)

    sql = _compile_sql(statement)
    assert "identity_memberships" in sql
    assert "identity_memberships.role" in sql
    assert "identity_memberships.status" in sql


def _run(awaitable: Any, session: SessionSpy) -> Any:
    import asyncio

    asyncio.run(awaitable)
    assert session.statement is not None
    return session.statement


def _compile_sql(statement: Any) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))
