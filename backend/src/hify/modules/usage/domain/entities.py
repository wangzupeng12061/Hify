from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from hify.modules.usage.domain.value_objects import (
    normalize_idempotency_key,
    normalize_model_name,
    normalize_provider,
    validate_cost_amount,
    validate_tokens,
)
from hify.shared.domain.ids import new_uuid


@dataclass(slots=True)
class UsageRecord:
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

    @classmethod
    def create(
        cls,
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
        now: datetime,
    ) -> UsageRecord:
        normalized_input_tokens = validate_tokens(input_tokens, "input_tokens")
        normalized_output_tokens = validate_tokens(output_tokens, "output_tokens")
        return cls(
            id=new_uuid(),
            team_id=team_id,
            user_id=user_id,
            run_id=run_id,
            agent_id=agent_id,
            agent_version_id=agent_version_id,
            provider_model_id=provider_model_id,
            provider=normalize_provider(provider),
            model=normalize_model_name(model),
            input_tokens=normalized_input_tokens,
            output_tokens=normalized_output_tokens,
            total_tokens=normalized_input_tokens + normalized_output_tokens,
            cost_amount=validate_cost_amount(cost_amount),
            idempotency_key=normalize_idempotency_key(idempotency_key),
            occurred_at=occurred_at,
            created_at=now,
        )
