from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from hify.modules.usage.contracts.dto import UsageQuotaStatusInfo, UsageRecordInfo, UsageSummaryInfo


class UsageRecorder(Protocol):
    async def record_model_usage(
        self,
        *,
        team_id: UUID,
        user_id: UUID,
        run_id: UUID,
        agent_id: UUID,
        agent_version_id: UUID,
        provider_model_id: UUID,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_amount: Decimal,
        idempotency_key: str,
        occurred_at: datetime,
    ) -> UsageRecordInfo: ...


class UsageReader(Protocol):
    async def get_team_summary(self, *, team_id: UUID) -> UsageSummaryInfo: ...

    async def get_run_summary(self, *, team_id: UUID, run_id: UUID) -> UsageSummaryInfo: ...


class UsageQuotaChecker(Protocol):
    async def ensure_team_quota_available(
        self,
        *,
        team_id: UUID,
        at: datetime,
    ) -> UsageQuotaStatusInfo: ...
