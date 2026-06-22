from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from uuid import UUID

from hify.modules.runs.domain.errors import RunStateConflictError
from hify.modules.runs.domain.value_objects import (
    TERMINAL_RUN_STATUSES,
    RunEventType,
    RunStatus,
    RunStepStatus,
    RunStepType,
    normalize_error_code,
    normalize_error_message,
    normalize_idempotency_key,
    normalize_step_name,
)
from hify.shared.domain.ids import new_uuid


@dataclass(slots=True)
class AgentRun:
    id: UUID
    team_id: UUID
    conversation_id: UUID
    agent_id: UUID
    agent_version_id: UUID
    status: RunStatus
    idempotency_key: str
    step_count: int
    event_count: int
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        conversation_id: UUID,
        agent_id: UUID,
        agent_version_id: UUID,
        idempotency_key: str,
        created_by: UUID,
        now: datetime,
    ) -> AgentRun:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            conversation_id=conversation_id,
            agent_id=agent_id,
            agent_version_id=agent_version_id,
            status=RunStatus.QUEUED,
            idempotency_key=normalize_idempotency_key(idempotency_key),
            step_count=0,
            event_count=0,
            version=0,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            started_at=None,
            completed_at=None,
            error_code=None,
            error_message=None,
        )

    def mark_running(self, now: datetime) -> None:
        if self.status is not RunStatus.QUEUED:
            raise RunStateConflictError("only queued runs can start")
        self.status = RunStatus.RUNNING
        self.started_at = now
        self._mark_updated(now)

    def mark_succeeded(self, now: datetime) -> None:
        self._ensure_can_finish()
        self.status = RunStatus.SUCCEEDED
        self.completed_at = now
        self._mark_updated(now)

    def mark_failed(self, *, error_code: str, error_message: str | None, now: datetime) -> None:
        self._ensure_can_finish()
        self.status = RunStatus.FAILED
        self.error_code = normalize_error_code(error_code)
        self.error_message = normalize_error_message(error_message)
        self.completed_at = now
        self._mark_updated(now)

    def mark_interrupted(
        self,
        *,
        error_code: str,
        error_message: str | None,
        now: datetime,
    ) -> None:
        self._ensure_can_finish()
        self.status = RunStatus.INTERRUPTED
        self.error_code = normalize_error_code(error_code)
        self.error_message = normalize_error_message(error_message)
        self.completed_at = now
        self._mark_updated(now)

    def cancel(self, now: datetime) -> None:
        if self.status in TERMINAL_RUN_STATUSES:
            raise RunStateConflictError("terminal runs cannot be cancelled")
        self.status = RunStatus.CANCELLED
        self.completed_at = now
        self._mark_updated(now)

    def create_step(
        self,
        *,
        step_type: RunStepType,
        name: str | None,
        now: datetime,
    ) -> RunStep:
        if self.status in TERMINAL_RUN_STATUSES:
            raise RunStateConflictError("terminal runs cannot create steps")
        self.step_count += 1
        self._mark_updated(now)
        return RunStep.create(
            team_id=self.team_id,
            run_id=self.id,
            sequence_number=self.step_count,
            step_type=step_type,
            name=name,
            now=now,
        )

    def create_event(
        self,
        *,
        event_type: RunEventType,
        payload: Mapping[str, object],
        now: datetime,
    ) -> RunEvent:
        self.event_count += 1
        self._mark_updated(now)
        return RunEvent.create(
            team_id=self.team_id,
            run_id=self.id,
            sequence_number=self.event_count,
            event_type=event_type,
            payload=payload,
            now=now,
        )

    def _ensure_can_finish(self) -> None:
        if self.status in TERMINAL_RUN_STATUSES:
            raise RunStateConflictError("terminal runs cannot change state")

    def _mark_updated(self, now: datetime) -> None:
        self.version += 1
        self.updated_at = now


@dataclass(slots=True)
class RunStep:
    id: UUID
    team_id: UUID
    run_id: UUID
    sequence_number: int
    step_type: RunStepType
    status: RunStepStatus
    name: str | None
    started_at: datetime
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        run_id: UUID,
        sequence_number: int,
        step_type: RunStepType,
        name: str | None,
        now: datetime,
    ) -> RunStep:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            run_id=run_id,
            sequence_number=sequence_number,
            step_type=step_type,
            status=RunStepStatus.STARTED,
            name=normalize_step_name(name),
            started_at=now,
            completed_at=None,
            error_code=None,
            error_message=None,
        )

    def mark_succeeded(self, now: datetime) -> None:
        if self.status is not RunStepStatus.STARTED:
            raise RunStateConflictError("only started steps can succeed")
        self.status = RunStepStatus.SUCCEEDED
        self.completed_at = now

    def mark_failed(self, *, error_code: str, error_message: str | None, now: datetime) -> None:
        if self.status is not RunStepStatus.STARTED:
            raise RunStateConflictError("only started steps can fail")
        self.status = RunStepStatus.FAILED
        self.error_code = normalize_error_code(error_code)
        self.error_message = normalize_error_message(error_message)
        self.completed_at = now

    def cancel(self, now: datetime) -> None:
        if self.status is not RunStepStatus.STARTED:
            raise RunStateConflictError("only started steps can be cancelled")
        self.status = RunStepStatus.CANCELLED
        self.completed_at = now


@dataclass(slots=True)
class RunEvent:
    id: UUID
    team_id: UUID
    run_id: UUID
    sequence_number: int
    event_type: RunEventType
    payload: Mapping[str, object]
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        run_id: UUID,
        sequence_number: int,
        event_type: RunEventType,
        payload: Mapping[str, object],
        now: datetime,
    ) -> RunEvent:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            run_id=run_id,
            sequence_number=sequence_number,
            event_type=event_type,
            payload=dict(payload),
            created_at=now,
        )
