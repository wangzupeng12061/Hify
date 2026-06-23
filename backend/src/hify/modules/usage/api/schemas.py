from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UsageSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: UUID
    run_id: UUID | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_amount: Decimal


class SetUsageQuotaRequest(BaseModel):
    monthly_token_limit: int | None


class UsageQuotaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: UUID
    monthly_token_limit: int | None
    version: int


class UsageQuotaStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: UUID
    monthly_token_limit: int | None
    used_tokens: int
    remaining_tokens: int | None
    is_exceeded: bool
    period_start: datetime
    period_end: datetime
