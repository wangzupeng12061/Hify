from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.usage.domain.entities import UsageQuota, UsageRecord
from hify.modules.usage.infrastructure.database.models import UsageQuotaModel, UsageRecordModel


class SqlAlchemyUsageRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: UsageRecord) -> None:
        self._session.add(_record_to_model(record))

    async def get_by_idempotency_key(
        self,
        *,
        team_id: UUID,
        idempotency_key: str,
    ) -> UsageRecord | None:
        statement = select(UsageRecordModel).where(
            UsageRecordModel.team_id == team_id,
            UsageRecordModel.idempotency_key == idempotency_key,
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _record_from_model(model)

    async def summarize_for_team(self, *, team_id: UUID) -> tuple[int, int, int, str]:
        statement = select(
            func.coalesce(func.sum(UsageRecordModel.input_tokens), 0),
            func.coalesce(func.sum(UsageRecordModel.output_tokens), 0),
            func.coalesce(func.sum(UsageRecordModel.total_tokens), 0),
            func.coalesce(func.sum(UsageRecordModel.cost_amount), Decimal("0")),
        ).where(UsageRecordModel.team_id == team_id)
        row = (await self._session.execute(statement)).one()
        return (int(row[0]), int(row[1]), int(row[2]), str(row[3]))

    async def summarize_for_run(self, *, team_id: UUID, run_id: UUID) -> tuple[int, int, int, str]:
        statement = select(
            func.coalesce(func.sum(UsageRecordModel.input_tokens), 0),
            func.coalesce(func.sum(UsageRecordModel.output_tokens), 0),
            func.coalesce(func.sum(UsageRecordModel.total_tokens), 0),
            func.coalesce(func.sum(UsageRecordModel.cost_amount), Decimal("0")),
        ).where(
            UsageRecordModel.team_id == team_id,
            UsageRecordModel.run_id == run_id,
        )
        row = (await self._session.execute(statement)).one()
        return (int(row[0]), int(row[1]), int(row[2]), str(row[3]))

    async def summarize_for_team_period(
        self,
        *,
        team_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[int, int, int, str]:
        statement = select(
            func.coalesce(func.sum(UsageRecordModel.input_tokens), 0),
            func.coalesce(func.sum(UsageRecordModel.output_tokens), 0),
            func.coalesce(func.sum(UsageRecordModel.total_tokens), 0),
            func.coalesce(func.sum(UsageRecordModel.cost_amount), Decimal("0")),
        ).where(
            UsageRecordModel.team_id == team_id,
            UsageRecordModel.occurred_at >= period_start,
            UsageRecordModel.occurred_at < period_end,
        )
        row = (await self._session.execute(statement)).one()
        return (int(row[0]), int(row[1]), int(row[2]), str(row[3]))

    async def summarize_by_model_for_team_period(
        self,
        *,
        team_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[tuple[UUID, str, str, int, int, int, str], ...]:
        statement = (
            select(
                UsageRecordModel.provider_model_id,
                UsageRecordModel.provider,
                UsageRecordModel.model,
                func.coalesce(func.sum(UsageRecordModel.input_tokens), 0),
                func.coalesce(func.sum(UsageRecordModel.output_tokens), 0),
                func.coalesce(func.sum(UsageRecordModel.total_tokens), 0),
                func.coalesce(func.sum(UsageRecordModel.cost_amount), Decimal("0")),
            )
            .where(
                UsageRecordModel.team_id == team_id,
                UsageRecordModel.occurred_at >= period_start,
                UsageRecordModel.occurred_at < period_end,
            )
            .group_by(
                UsageRecordModel.provider_model_id,
                UsageRecordModel.provider,
                UsageRecordModel.model,
            )
            .order_by(func.sum(UsageRecordModel.cost_amount).desc(), UsageRecordModel.model.asc())
        )
        rows = await self._session.execute(statement)
        return tuple(
            (
                row[0],
                str(row[1]),
                str(row[2]),
                int(row[3]),
                int(row[4]),
                int(row[5]),
                str(row[6]),
            )
            for row in rows
        )

    async def summarize_by_day_for_team_period(
        self,
        *,
        team_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[tuple[date, int, int, int, str], ...]:
        usage_day = func.date_trunc("day", UsageRecordModel.occurred_at).label("usage_day")
        statement = (
            select(
                usage_day,
                func.coalesce(func.sum(UsageRecordModel.input_tokens), 0),
                func.coalesce(func.sum(UsageRecordModel.output_tokens), 0),
                func.coalesce(func.sum(UsageRecordModel.total_tokens), 0),
                func.coalesce(func.sum(UsageRecordModel.cost_amount), Decimal("0")),
            )
            .where(
                UsageRecordModel.team_id == team_id,
                UsageRecordModel.occurred_at >= period_start,
                UsageRecordModel.occurred_at < period_end,
            )
            .group_by(usage_day)
            .order_by(usage_day.asc())
        )
        rows = await self._session.execute(statement)
        return tuple(
            (
                row[0].date() if isinstance(row[0], datetime) else row[0],
                int(row[1]),
                int(row[2]),
                int(row[3]),
                str(row[4]),
            )
            for row in rows
        )


class SqlAlchemyUsageQuotaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, quota: UsageQuota) -> None:
        self._session.add(_quota_to_model(quota))

    async def save(self, quota: UsageQuota) -> None:
        model = await self._session.get(UsageQuotaModel, quota.id)
        if model is None:
            self._session.add(_quota_to_model(quota))
            return
        model.monthly_token_limit = quota.monthly_token_limit
        model.version = quota.version
        model.updated_by = quota.updated_by
        model.updated_at = quota.updated_at

    async def get_by_team(self, *, team_id: UUID) -> UsageQuota | None:
        statement = select(UsageQuotaModel).where(UsageQuotaModel.team_id == team_id)
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _quota_from_model(model)


def _record_to_model(record: UsageRecord) -> UsageRecordModel:
    return UsageRecordModel(
        id=record.id,
        team_id=record.team_id,
        user_id=record.user_id,
        run_id=record.run_id,
        agent_id=record.agent_id,
        agent_version_id=record.agent_version_id,
        provider_model_id=record.provider_model_id,
        provider=record.provider,
        model=record.model,
        input_tokens=record.input_tokens,
        output_tokens=record.output_tokens,
        total_tokens=record.total_tokens,
        cost_amount=record.cost_amount,
        idempotency_key=record.idempotency_key,
        occurred_at=record.occurred_at,
        created_at=record.created_at,
    )


def _record_from_model(model: UsageRecordModel) -> UsageRecord:
    return UsageRecord(
        id=model.id,
        team_id=model.team_id,
        user_id=model.user_id,
        run_id=model.run_id,
        agent_id=model.agent_id,
        agent_version_id=model.agent_version_id,
        provider_model_id=model.provider_model_id,
        provider=model.provider,
        model=model.model,
        input_tokens=model.input_tokens,
        output_tokens=model.output_tokens,
        total_tokens=model.total_tokens,
        cost_amount=model.cost_amount,
        idempotency_key=model.idempotency_key,
        occurred_at=model.occurred_at,
        created_at=model.created_at,
    )


def _quota_to_model(quota: UsageQuota) -> UsageQuotaModel:
    return UsageQuotaModel(
        id=quota.id,
        team_id=quota.team_id,
        monthly_token_limit=quota.monthly_token_limit,
        version=quota.version,
        created_by=quota.created_by,
        updated_by=quota.updated_by,
        created_at=quota.created_at,
        updated_at=quota.updated_at,
    )


def _quota_from_model(model: UsageQuotaModel) -> UsageQuota:
    return UsageQuota(
        id=model.id,
        team_id=model.team_id,
        monthly_token_limit=model.monthly_token_limit,
        version=model.version,
        created_by=model.created_by,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
