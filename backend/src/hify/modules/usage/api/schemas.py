from __future__ import annotations

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
