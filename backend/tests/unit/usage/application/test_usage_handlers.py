from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.providers.contracts.dto import ModelPricingInfo
from hify.modules.usage.application.commands.record_model_usage import (
    RecordModelUsageCommand,
    RecordModelUsageHandler,
)
from hify.modules.usage.application.commands.set_team_usage_quota import (
    SetTeamUsageQuotaCommand,
    SetTeamUsageQuotaHandler,
)
from hify.modules.usage.application.quota_checker import UsageQuotaCheckerService
from hify.modules.usage.application.queries.get_team_usage_quota_status import (
    GetTeamUsageQuotaStatusHandler,
    GetTeamUsageQuotaStatusQuery,
)
from hify.modules.usage.application.queries.get_run_usage_summary import (
    GetRunUsageSummaryHandler,
    GetRunUsageSummaryQuery,
)
from hify.modules.usage.application.queries.get_team_usage_summary import (
    GetTeamUsageSummaryHandler,
    GetTeamUsageSummaryQuery,
)
from hify.modules.usage.contracts.errors import UsageQuotaExceededError
from hify.modules.usage.domain.entities import UsageQuota, UsageRecord
from hify.modules.usage.domain.errors import UsagePermissionDeniedError
from hify.shared.domain.clock import Clock


NOW = datetime(2026, 6, 22, tzinfo=UTC)
TEAM_ID = UUID("00000000-0000-7000-8000-000000000001")
USER_ID = UUID("00000000-0000-7000-8000-000000000002")
MEMBERSHIP_ID = UUID("00000000-0000-7000-8000-000000000003")
RUN_ID = UUID("00000000-0000-7000-8000-000000000004")
AGENT_ID = UUID("00000000-0000-7000-8000-000000000005")
AGENT_VERSION_ID = UUID("00000000-0000-7000-8000-000000000006")
PROVIDER_MODEL_ID = UUID("00000000-0000-7000-8000-000000000007")


class FixedClock(Clock):
    def now(self) -> datetime:
        return NOW


class FakeUsageRecordRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, UsageRecord] = {}

    async def add(self, record: UsageRecord) -> None:
        self.items[record.id] = record

    async def get_by_idempotency_key(
        self,
        *,
        team_id: UUID,
        idempotency_key: str,
    ) -> UsageRecord | None:
        for record in self.items.values():
            if record.team_id == team_id and record.idempotency_key == idempotency_key:
                return record
        return None

    async def summarize_for_team(self, *, team_id: UUID) -> tuple[int, int, int, str]:
        records = [record for record in self.items.values() if record.team_id == team_id]
        return _summarize(records)

    async def summarize_for_run(self, *, team_id: UUID, run_id: UUID) -> tuple[int, int, int, str]:
        records = [
            record
            for record in self.items.values()
            if record.team_id == team_id and record.run_id == run_id
        ]
        return _summarize(records)

    async def summarize_for_team_period(
        self,
        *,
        team_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[int, int, int, str]:
        records = [
            record
            for record in self.items.values()
            if record.team_id == team_id
            and period_start <= record.occurred_at < period_end
        ]
        return _summarize(records)


class FakeUsageQuotaRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, UsageQuota] = {}

    async def add(self, quota: UsageQuota) -> None:
        self.items[quota.id] = quota

    async def save(self, quota: UsageQuota) -> None:
        self.items[quota.id] = quota

    async def get_by_team(self, *, team_id: UUID) -> UsageQuota | None:
        for quota in self.items.values():
            if quota.team_id == team_id:
                return quota
        return None


class FakeUsageUnitOfWork:
    def __init__(self) -> None:
        self.records = FakeUsageRecordRepository()
        self.quotas = FakeUsageQuotaRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeModelPricingCatalog:
    def __init__(self, pricing: ModelPricingInfo | None) -> None:
        self.pricing = pricing
        self.requests: list[tuple[UUID, UUID]] = []

    async def get_model_pricing(
        self,
        *,
        team_id: UUID,
        model_id: UUID,
    ) -> ModelPricingInfo | None:
        self.requests.append((team_id, model_id))
        return self.pricing


def actor_with_usage_read() -> ActorContext:
    return ActorContext(
        user_id=USER_ID,
        team_id=TEAM_ID,
        membership_id=MEMBERSHIP_ID,
        role="admin",
        permissions=("usage.read",),
    )


def actor_with_usage_manage() -> ActorContext:
    return ActorContext(
        user_id=USER_ID,
        team_id=TEAM_ID,
        membership_id=MEMBERSHIP_ID,
        role="admin",
        permissions=("usage.read", "usage.manage"),
    )


@pytest.mark.asyncio
async def test_record_model_usage_is_idempotent_by_team_key() -> None:
    unit_of_work = FakeUsageUnitOfWork()
    handler = RecordModelUsageHandler(lambda: unit_of_work, FixedClock())
    command = _record_command(input_tokens=11, output_tokens=7, idempotency_key="usage-1")

    first = await handler.handle(command)
    second = await handler.handle(
        _record_command(input_tokens=99, output_tokens=99, idempotency_key="usage-1")
    )

    assert first == second
    assert first.input_tokens == 11
    assert first.output_tokens == 7
    assert first.total_tokens == 18
    assert len(unit_of_work.records.items) == 1
    assert unit_of_work.committed


@pytest.mark.asyncio
async def test_record_model_usage_estimates_cost_from_provider_pricing() -> None:
    unit_of_work = FakeUsageUnitOfWork()
    pricing_catalog = FakeModelPricingCatalog(
        ModelPricingInfo(
            provider_model_id=PROVIDER_MODEL_ID,
            team_id=TEAM_ID,
            price_per_1m_input_tokens=Decimal("2.00000000"),
            price_per_1m_output_tokens=Decimal("8.00000000"),
        )
    )
    handler = RecordModelUsageHandler(lambda: unit_of_work, FixedClock(), pricing_catalog)

    record = await handler.handle(
        _record_command(input_tokens=1000, output_tokens=2000, idempotency_key="priced")
    )

    assert record.cost_amount == Decimal("0.01800000")
    assert pricing_catalog.requests == [(TEAM_ID, PROVIDER_MODEL_ID)]


@pytest.mark.asyncio
async def test_record_model_usage_uses_zero_cost_when_pricing_is_missing() -> None:
    unit_of_work = FakeUsageUnitOfWork()
    pricing_catalog = FakeModelPricingCatalog(None)
    handler = RecordModelUsageHandler(lambda: unit_of_work, FixedClock(), pricing_catalog)

    record = await handler.handle(
        _record_command(input_tokens=1000, output_tokens=2000, idempotency_key="unpriced")
    )

    assert record.cost_amount == Decimal("0E-8")


@pytest.mark.asyncio
async def test_record_model_usage_does_not_reprice_existing_idempotent_record() -> None:
    unit_of_work = FakeUsageUnitOfWork()
    pricing_catalog = FakeModelPricingCatalog(
        ModelPricingInfo(
            provider_model_id=PROVIDER_MODEL_ID,
            team_id=TEAM_ID,
            price_per_1m_input_tokens=Decimal("1.00000000"),
            price_per_1m_output_tokens=Decimal("1.00000000"),
        )
    )
    handler = RecordModelUsageHandler(lambda: unit_of_work, FixedClock(), pricing_catalog)
    first = await handler.handle(
        _record_command(input_tokens=1000, output_tokens=1000, idempotency_key="same")
    )
    pricing_catalog.pricing = ModelPricingInfo(
        provider_model_id=PROVIDER_MODEL_ID,
        team_id=TEAM_ID,
        price_per_1m_input_tokens=Decimal("99.00000000"),
        price_per_1m_output_tokens=Decimal("99.00000000"),
    )

    second = await handler.handle(
        _record_command(input_tokens=1000, output_tokens=1000, idempotency_key="same")
    )

    assert second == first
    assert second.cost_amount == Decimal("0.00200000")
    assert pricing_catalog.requests == [(TEAM_ID, PROVIDER_MODEL_ID)]


@pytest.mark.asyncio
async def test_usage_summary_handlers_sum_team_and_run_usage() -> None:
    unit_of_work = FakeUsageUnitOfWork()
    record_handler = RecordModelUsageHandler(lambda: unit_of_work, FixedClock())
    await record_handler.handle(_record_command(input_tokens=3, output_tokens=5, idempotency_key="a"))
    await record_handler.handle(_record_command(input_tokens=7, output_tokens=11, idempotency_key="b"))
    actor = actor_with_usage_read()

    team_summary = await GetTeamUsageSummaryHandler(lambda: unit_of_work).handle(
        GetTeamUsageSummaryQuery(actor=actor)
    )
    run_summary = await GetRunUsageSummaryHandler(lambda: unit_of_work).handle(
        GetRunUsageSummaryQuery(actor=actor, run_id=RUN_ID)
    )

    assert team_summary.input_tokens == 10
    assert team_summary.output_tokens == 16
    assert team_summary.total_tokens == 26
    assert run_summary.run_id == RUN_ID
    assert run_summary.total_tokens == 26


@pytest.mark.asyncio
async def test_usage_summary_requires_usage_read_permission() -> None:
    actor = ActorContext(
        user_id=USER_ID,
        team_id=TEAM_ID,
        membership_id=MEMBERSHIP_ID,
        role="member",
        permissions=("runs.read",),
    )

    with pytest.raises(UsagePermissionDeniedError):
        await GetTeamUsageSummaryHandler(lambda: FakeUsageUnitOfWork()).handle(
            GetTeamUsageSummaryQuery(actor=actor)
        )


@pytest.mark.asyncio
async def test_set_team_usage_quota_creates_and_updates_quota() -> None:
    unit_of_work = FakeUsageUnitOfWork()
    actor = actor_with_usage_manage()
    handler = SetTeamUsageQuotaHandler(lambda: unit_of_work, FixedClock())

    created = await handler.handle(
        SetTeamUsageQuotaCommand(actor=actor, monthly_token_limit=100)
    )
    updated = await handler.handle(
        SetTeamUsageQuotaCommand(actor=actor, monthly_token_limit=200)
    )

    assert created.id == updated.id
    assert updated.monthly_token_limit == 200
    assert updated.version == 1
    assert len(unit_of_work.quotas.items) == 1
    assert unit_of_work.committed


@pytest.mark.asyncio
async def test_quota_status_uses_current_month_usage() -> None:
    unit_of_work = FakeUsageUnitOfWork()
    actor = actor_with_usage_manage()
    await SetTeamUsageQuotaHandler(lambda: unit_of_work, FixedClock()).handle(
        SetTeamUsageQuotaCommand(actor=actor, monthly_token_limit=100)
    )
    await RecordModelUsageHandler(lambda: unit_of_work, FixedClock()).handle(
        _record_command(input_tokens=30, output_tokens=40, idempotency_key="usage-1")
    )

    status_info = await GetTeamUsageQuotaStatusHandler(lambda: unit_of_work, FixedClock()).handle(
        GetTeamUsageQuotaStatusQuery(actor=actor)
    )

    assert status_info.monthly_token_limit == 100
    assert status_info.used_tokens == 70
    assert status_info.remaining_tokens == 30
    assert not status_info.is_exceeded
    assert status_info.period_start == datetime(2026, 6, 1, tzinfo=UTC)
    assert status_info.period_end == datetime(2026, 7, 1, tzinfo=UTC)


@pytest.mark.asyncio
async def test_quota_checker_rejects_when_monthly_limit_is_exceeded() -> None:
    unit_of_work = FakeUsageUnitOfWork()
    actor = actor_with_usage_manage()
    await SetTeamUsageQuotaHandler(lambda: unit_of_work, FixedClock()).handle(
        SetTeamUsageQuotaCommand(actor=actor, monthly_token_limit=70)
    )
    await RecordModelUsageHandler(lambda: unit_of_work, FixedClock()).handle(
        _record_command(input_tokens=30, output_tokens=40, idempotency_key="usage-1")
    )

    with pytest.raises(UsageQuotaExceededError):
        await UsageQuotaCheckerService(lambda: unit_of_work).ensure_team_quota_available(
            team_id=TEAM_ID,
            at=NOW,
        )


@pytest.mark.asyncio
async def test_quota_checker_allows_when_quota_is_not_configured() -> None:
    status_info = await UsageQuotaCheckerService(
        lambda: FakeUsageUnitOfWork()
    ).ensure_team_quota_available(team_id=TEAM_ID, at=NOW)

    assert status_info.monthly_token_limit is None
    assert status_info.remaining_tokens is None
    assert not status_info.is_exceeded


def _record_command(
    *,
    input_tokens: int,
    output_tokens: int,
    idempotency_key: str,
) -> RecordModelUsageCommand:
    return RecordModelUsageCommand(
        team_id=TEAM_ID,
        user_id=USER_ID,
        run_id=RUN_ID,
        agent_id=AGENT_ID,
        agent_version_id=AGENT_VERSION_ID,
        provider_model_id=PROVIDER_MODEL_ID,
        provider="openai",
        model="gpt-4.1",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_amount=Decimal("0"),
        idempotency_key=idempotency_key,
        occurred_at=NOW,
    )


def _summarize(records: list[UsageRecord]) -> tuple[int, int, int, str]:
    input_tokens = sum(record.input_tokens for record in records)
    output_tokens = sum(record.output_tokens for record in records)
    total_tokens = sum(record.total_tokens for record in records)
    cost_amount = sum((record.cost_amount for record in records), Decimal("0"))
    return (input_tokens, output_tokens, total_tokens, str(cost_amount))
