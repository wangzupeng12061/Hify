from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.jobs.infrastructure.database.models import JobModel
from hify.modules.jobs.infrastructure.database.repositories import SqlAlchemyJobRepository


class SessionSpy:
    def __init__(self) -> None:
        self.statement: Any | None = None

    async def scalar(self, statement: Any) -> None:
        self.statement = statement
        return None


def test_claim_next_uses_queue_available_filter_and_skip_locked() -> None:
    session = SessionSpy()
    repository = SqlAlchemyJobRepository(cast(AsyncSession, session))
    now = datetime(2026, 6, 22, tzinfo=UTC)

    _run(
        repository.claim_next(
            queue="ingestion",
            lease_owner="worker-1",
            lease_expires_at=now + timedelta(minutes=5),
            now=now,
        ),
        session,
    )

    sql = _compile_sql(session.statement)
    assert "jobs_jobs.queue" in sql
    assert "jobs_jobs.available_at" in sql
    assert "jobs_jobs.lease_expires_at" in sql
    assert "FOR UPDATE SKIP LOCKED" in sql


def test_job_model_has_idempotency_and_partial_indexes() -> None:
    index_names = {index.name for index in JobModel.__table__.indexes}

    assert "uq_jobs_jobs__team_idempotency_key" in index_names
    assert "pix_jobs_jobs__pending_queue_available" in index_names
    assert "pix_jobs_jobs__running_lease_expired" in index_names


def _run(awaitable: Any, session: SessionSpy) -> None:
    import asyncio

    asyncio.run(awaitable)
    assert session.statement is not None


def _compile_sql(statement: Any) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))
