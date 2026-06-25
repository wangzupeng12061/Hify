from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from hify.modules.runs.domain.errors import RunValidationError


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class RunStepType(StrEnum):
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    RETRIEVAL = "retrieval"
    SYSTEM = "system"


class RunStepStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunEventType(StrEnum):
    RUN_CREATED = "run.created"
    RUN_STARTED = "run.started"
    RUN_SUCCEEDED = "run.succeeded"
    RUN_FAILED = "run.failed"
    RUN_CANCELLED = "run.cancelled"
    RUN_INTERRUPTED = "run.interrupted"
    STEP_STARTED = "step.started"
    STEP_SUCCEEDED = "step.succeeded"
    STEP_FAILED = "step.failed"
    OUTPUT_TEXT_DELTA = "output.text_delta"
    DIAGNOSTIC = "diagnostic"
    ACTIVITY_STARTED = "activity.started"
    ACTIVITY_COMPLETED = "activity.completed"
    SOURCE_DISCOVERED = "source.discovered"


TERMINAL_RUN_STATUSES = frozenset(
    {
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
        RunStatus.INTERRUPTED,
    }
)


def normalize_idempotency_key(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise RunValidationError("idempotency key must not be blank")
    if len(normalized) > 120:
        raise RunValidationError("idempotency key must be at most 120 characters")
    return normalized


def normalize_step_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    if len(normalized) > 120:
        raise RunValidationError("step name must be at most 120 characters")
    return normalized


def normalize_error_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    if not normalized:
        return None
    if len(normalized) > 120:
        raise RunValidationError("error code must be at most 120 characters")
    return normalized


def normalize_error_message(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > 1000:
        raise RunValidationError("error message must be at most 1000 characters")
    return normalized


def duration_ms_between(started_at: datetime, finished_at: datetime) -> int:
    duration_seconds = finished_at.timestamp() - started_at.timestamp()
    return max(int(duration_seconds * 1000), 0)


def parse_event_cursor(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        cursor = int(value)
    except ValueError as exc:
        raise RunValidationError("run event cursor is invalid") from exc
    if cursor < 0:
        raise RunValidationError("run event cursor is invalid")
    return cursor
