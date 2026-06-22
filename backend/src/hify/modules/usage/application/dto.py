from __future__ import annotations

from hify.modules.usage.contracts.dto import UsageRecordInfo
from hify.modules.usage.domain.entities import UsageRecord


def usage_record_info_from_domain(record: UsageRecord) -> UsageRecordInfo:
    return UsageRecordInfo(
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
