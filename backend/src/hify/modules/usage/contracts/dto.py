from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UsageRecordInfo:
    id: UUID
    team_id: UUID
    user_id: UUID
    run_id: UUID
    agent_id: UUID
    agent_version_id: UUID
    provider_model_id: UUID
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_amount: Decimal
    idempotency_key: str
    occurred_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class UsageSummaryInfo:
    team_id: UUID
    run_id: UUID | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_amount: Decimal


@dataclass(frozen=True, slots=True)
class UsageQuotaInfo:
    id: UUID
    team_id: UUID
    monthly_token_limit: int | None
    version: int
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class UsageQuotaStatusInfo:
    team_id: UUID
    monthly_token_limit: int | None
    used_tokens: int
    remaining_tokens: int | None
    is_exceeded: bool
    period_start: datetime
    period_end: datetime
