from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.runs.domain.entities import AgentRun, RunEvent, RunStep
from hify.modules.runs.domain.value_objects import (
    RunEventType,
    RunStatus,
    RunStepStatus,
    RunStepType,
)
from hify.modules.runs.infrastructure.database.models import (
    RunEventModel,
    RunModel,
    RunStepModel,
)


class SqlAlchemyRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, run: AgentRun) -> None:
        self._session.add(_run_to_model(run))

    async def save(self, run: AgentRun) -> None:
        model = await self._session.get(RunModel, run.id)
        if model is None:
            self._session.add(_run_to_model(run))
            return
        model.status = run.status.value
        model.step_count = run.step_count
        model.event_count = run.event_count
        model.version = run.version
        model.updated_at = run.updated_at
        model.started_at = run.started_at
        model.completed_at = run.completed_at
        model.error_code = run.error_code
        model.error_message = run.error_message

    async def get_by_id(self, run_id: UUID) -> AgentRun | None:
        model = await self._session.get(RunModel, run_id)
        if model is None:
            return None
        return _run_from_model(model)

    async def get_by_idempotency_key(
        self,
        *,
        team_id: UUID,
        conversation_id: UUID,
        idempotency_key: str,
    ) -> AgentRun | None:
        statement = select(RunModel).where(
            RunModel.team_id == team_id,
            RunModel.conversation_id == conversation_id,
            RunModel.idempotency_key == idempotency_key,
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _run_from_model(model)


class SqlAlchemyRunStepRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, step: RunStep) -> None:
        self._session.add(_step_to_model(step))

    async def get_by_id(self, step_id: UUID) -> RunStep | None:
        model = await self._session.get(RunStepModel, step_id)
        if model is None:
            return None
        return _step_from_model(model)

    async def list_by_run(self, *, run_id: UUID) -> tuple[RunStep, ...]:
        statement = (
            select(RunStepModel)
            .where(RunStepModel.run_id == run_id)
            .order_by(RunStepModel.sequence_number.asc())
        )
        models = (await self._session.scalars(statement)).all()
        return tuple(_step_from_model(model) for model in models)


class SqlAlchemyRunEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: RunEvent) -> None:
        self._session.add(_event_to_model(event))

    async def list_by_run(
        self,
        *,
        run_id: UUID,
        after_sequence_number: int | None,
        limit: int,
    ) -> tuple[RunEvent, ...]:
        statement = (
            select(RunEventModel)
            .where(RunEventModel.run_id == run_id)
            .order_by(RunEventModel.sequence_number.asc())
            .limit(limit)
        )
        if after_sequence_number is not None:
            statement = statement.where(RunEventModel.sequence_number > after_sequence_number)
        models = (await self._session.scalars(statement)).all()
        return tuple(_event_from_model(model) for model in models)


def _run_to_model(run: AgentRun) -> RunModel:
    return RunModel(
        id=run.id,
        team_id=run.team_id,
        conversation_id=run.conversation_id,
        agent_id=run.agent_id,
        agent_version_id=run.agent_version_id,
        status=run.status.value,
        idempotency_key=run.idempotency_key,
        step_count=run.step_count,
        event_count=run.event_count,
        version=run.version,
        created_by=run.created_by,
        created_at=run.created_at,
        updated_at=run.updated_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        error_code=run.error_code,
        error_message=run.error_message,
    )


def _run_from_model(model: RunModel) -> AgentRun:
    return AgentRun(
        id=model.id,
        team_id=model.team_id,
        conversation_id=model.conversation_id,
        agent_id=model.agent_id,
        agent_version_id=model.agent_version_id,
        status=RunStatus(model.status),
        idempotency_key=model.idempotency_key,
        step_count=model.step_count,
        event_count=model.event_count,
        version=model.version,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
        started_at=model.started_at,
        completed_at=model.completed_at,
        error_code=model.error_code,
        error_message=model.error_message,
    )


def _step_to_model(step: RunStep) -> RunStepModel:
    return RunStepModel(
        id=step.id,
        team_id=step.team_id,
        run_id=step.run_id,
        sequence_number=step.sequence_number,
        step_type=step.step_type.value,
        status=step.status.value,
        name=step.name,
        started_at=step.started_at,
        completed_at=step.completed_at,
        error_code=step.error_code,
        error_message=step.error_message,
    )


def _step_from_model(model: RunStepModel) -> RunStep:
    return RunStep(
        id=model.id,
        team_id=model.team_id,
        run_id=model.run_id,
        sequence_number=model.sequence_number,
        step_type=RunStepType(model.step_type),
        status=RunStepStatus(model.status),
        name=model.name,
        started_at=model.started_at,
        completed_at=model.completed_at,
        error_code=model.error_code,
        error_message=model.error_message,
    )


def _event_to_model(event: RunEvent) -> RunEventModel:
    return RunEventModel(
        id=event.id,
        team_id=event.team_id,
        run_id=event.run_id,
        sequence_number=event.sequence_number,
        event_type=event.event_type.value,
        payload=dict(event.payload),
        created_at=event.created_at,
    )


def _event_from_model(model: RunEventModel) -> RunEvent:
    return RunEvent(
        id=model.id,
        team_id=model.team_id,
        run_id=model.run_id,
        sequence_number=model.sequence_number,
        event_type=RunEventType(model.event_type),
        payload=model.payload,
        created_at=model.created_at,
    )
