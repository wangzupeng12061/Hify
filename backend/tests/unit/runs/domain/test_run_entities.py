from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from hify.modules.runs.domain.entities import AgentRun
from hify.modules.runs.domain.errors import RunStateConflictError
from hify.modules.runs.domain.value_objects import RunEventType, RunStatus, RunStepType


def test_create_run_and_event_increment_counts() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)

    run = AgentRun.create(
        team_id=UUID("00000000-0000-7000-8000-000000000001"),
        conversation_id=UUID("00000000-0000-7000-8000-000000000002"),
        agent_id=UUID("00000000-0000-7000-8000-000000000003"),
        agent_version_id=UUID("00000000-0000-7000-8000-000000000004"),
        idempotency_key=" request-1 ",
        created_by=UUID("00000000-0000-7000-8000-000000000005"),
        now=now,
    )
    event = run.create_event(
        event_type=RunEventType.RUN_CREATED,
        payload={"agent_version_id": str(run.agent_version_id)},
        now=now,
    )

    assert run.status == RunStatus.QUEUED
    assert run.idempotency_key == "request-1"
    assert run.event_count == 1
    assert event.sequence_number == 1


def test_run_lifecycle_rejects_terminal_state_changes() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)
    run = _create_run(now)

    run.mark_running(now)
    run.mark_succeeded(now)

    with pytest.raises(RunStateConflictError):
        run.cancel(now)


def test_run_and_step_record_duration_and_cancel_code() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)
    finished_at = now + timedelta(seconds=2, milliseconds=150)
    run = _create_run(now)

    run.mark_running(now)
    step = run.create_step(step_type=RunStepType.LLM_CALL, name="Model call", now=now)
    step.cancel(finished_at)
    run.cancel(finished_at)

    assert step.duration_ms == 2150
    assert step.error_code == "RUN_CANCELLED"
    assert run.duration_ms == 2150
    assert run.error_code == "RUN_CANCELLED"


def test_create_step_increments_step_count() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)
    run = _create_run(now)

    step = run.create_step(step_type=RunStepType.LLM_CALL, name="  Model call ", now=now)
    step.mark_succeeded(now)

    assert run.step_count == 1
    assert step.sequence_number == 1
    assert step.name == "Model call"
    assert step.completed_at == now


def _create_run(now: datetime) -> AgentRun:
    return AgentRun.create(
        team_id=UUID("00000000-0000-7000-8000-000000000001"),
        conversation_id=UUID("00000000-0000-7000-8000-000000000002"),
        agent_id=UUID("00000000-0000-7000-8000-000000000003"),
        agent_version_id=UUID("00000000-0000-7000-8000-000000000004"),
        idempotency_key="request-1",
        created_by=UUID("00000000-0000-7000-8000-000000000005"),
        now=now,
    )
