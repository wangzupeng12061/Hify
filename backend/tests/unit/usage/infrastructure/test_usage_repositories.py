from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.usage.infrastructure.database.models import UsageQuotaModel, UsageRecordModel
from hify.modules.usage.infrastructure.database.repositories import SqlAlchemyUsageRecordRepository


class SessionSpy:
    def __init__(self) -> None:
        self.statement: Any | None = None

    async def execute(self, statement: Any) -> "ResultSpy":
        self.statement = statement
        return ResultSpy()


class ResultSpy:
    def one(self) -> tuple[int, int, int, str]:
        return (0, 0, 0, "0")

    def __iter__(self) -> "ResultSpy":
        return self

    def __next__(self) -> tuple[Any, ...]:
        raise StopIteration


def test_usage_model_has_idempotency_and_summary_indexes() -> None:
    index_names = {index.name for index in UsageRecordModel.__table__.indexes}

    assert "uq_usage_records__team_idempotency_key" in index_names
    assert "ix_usage_records__team_occurred_id" in index_names
    assert "ix_usage_records__team_run_occurred_id" in index_names


def test_usage_quota_model_has_team_unique_index() -> None:
    index_names = {index.name for index in UsageQuotaModel.__table__.indexes}

    assert "uq_usage_quotas__team" in index_names


def test_run_summary_filters_by_team_and_run() -> None:
    session = SessionSpy()
    repository = SqlAlchemyUsageRecordRepository(cast(AsyncSession, session))

    _run(
        repository.summarize_for_run(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            run_id=UUID("00000000-0000-7000-8000-000000000002"),
        ),
        session,
    )

    sql = _compile_sql(session.statement)
    assert "usage_records.team_id" in sql
    assert "usage_records.run_id" in sql
    assert "sum(usage_records.input_tokens)" in sql


def test_team_period_summary_filters_by_month_range() -> None:
    session = SessionSpy()
    repository = SqlAlchemyUsageRecordRepository(cast(AsyncSession, session))

    _run(
        repository.summarize_for_team_period(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            period_start=datetime(2026, 6, 1, tzinfo=UTC),
            period_end=datetime(2026, 7, 1, tzinfo=UTC),
        ),
        session,
    )

    sql = _compile_sql(session.statement)
    assert "usage_records.team_id" in sql
    assert "usage_records.occurred_at >=" in sql
    assert "usage_records.occurred_at <" in sql


def test_model_cost_summary_groups_by_model_for_period() -> None:
    session = SessionSpy()
    repository = SqlAlchemyUsageRecordRepository(cast(AsyncSession, session))

    _run(
        repository.summarize_by_model_for_team_period(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            period_start=datetime(2026, 6, 1, tzinfo=UTC),
            period_end=datetime(2026, 7, 1, tzinfo=UTC),
        ),
        session,
    )

    sql = _compile_sql(session.statement)
    assert "usage_records.team_id" in sql
    assert "usage_records.occurred_at >=" in sql
    assert "GROUP BY usage_records.provider_model_id" in sql
    assert "sum(usage_records.cost_amount)" in sql


def test_daily_cost_summary_groups_by_day_for_period() -> None:
    session = SessionSpy()
    repository = SqlAlchemyUsageRecordRepository(cast(AsyncSession, session))

    _run(
        repository.summarize_by_day_for_team_period(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            period_start=datetime(2026, 6, 1, tzinfo=UTC),
            period_end=datetime(2026, 7, 1, tzinfo=UTC),
        ),
        session,
    )

    sql = _compile_sql(session.statement)
    assert "date_trunc" in sql
    assert "usage_records.team_id" in sql
    assert "usage_records.occurred_at <" in sql
    assert "GROUP BY date_trunc" in sql


def _run(awaitable: Any, session: SessionSpy) -> None:
    import asyncio

    asyncio.run(awaitable)
    assert session.statement is not None


def _compile_sql(statement: Any) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))
