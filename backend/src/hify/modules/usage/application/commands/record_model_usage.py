from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from hify.modules.usage.application.dto import usage_record_info_from_domain
from hify.modules.usage.application.ports import UsageUnitOfWorkFactory
from hify.modules.usage.contracts.dto import UsageRecordInfo
from hify.modules.usage.contracts.services import UsageRecorder
from hify.modules.usage.domain.entities import UsageRecord
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class RecordModelUsageCommand:
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
    cost_amount: Decimal
    idempotency_key: str
    occurred_at: datetime


class RecordModelUsageHandler:
    def __init__(self, unit_of_work_factory: UsageUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: RecordModelUsageCommand) -> UsageRecordInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            existing_record = await unit_of_work.records.get_by_idempotency_key(
                team_id=command.team_id,
                idempotency_key=command.idempotency_key,
            )
            if existing_record is not None:
                return usage_record_info_from_domain(existing_record)

            record = UsageRecord.create(
                team_id=command.team_id,
                user_id=command.user_id,
                run_id=command.run_id,
                agent_id=command.agent_id,
                agent_version_id=command.agent_version_id,
                provider_model_id=command.provider_model_id,
                provider=command.provider,
                model=command.model,
                input_tokens=command.input_tokens,
                output_tokens=command.output_tokens,
                cost_amount=command.cost_amount,
                idempotency_key=command.idempotency_key,
                occurred_at=command.occurred_at,
                now=self._clock.now(),
            )
            await unit_of_work.records.add(record)
            await unit_of_work.commit()

        return usage_record_info_from_domain(record)


class UsageRecorderService(UsageRecorder):
    def __init__(self, record_model_usage_handler: RecordModelUsageHandler) -> None:
        self._record_model_usage_handler = record_model_usage_handler

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
    ) -> UsageRecordInfo:
        return await self._record_model_usage_handler.handle(
            RecordModelUsageCommand(
                team_id=team_id,
                user_id=user_id,
                run_id=run_id,
                agent_id=agent_id,
                agent_version_id=agent_version_id,
                provider_model_id=provider_model_id,
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_amount=cost_amount,
                idempotency_key=idempotency_key,
                occurred_at=occurred_at,
            )
        )
