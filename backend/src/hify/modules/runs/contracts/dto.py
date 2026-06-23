from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Mapping
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RunInfo:
    id: UUID
    team_id: UUID
    conversation_id: UUID
    agent_id: UUID
    agent_version_id: UUID
    status: str
    step_count: int
    event_count: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class RunStepInfo:
    id: UUID
    team_id: UUID
    run_id: UUID
    sequence_number: int
    step_type: str
    status: str
    name: str | None
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class RunDiagnosticStepInfo:
    id: UUID
    sequence_number: int
    step_type: str
    status: str
    name: str | None
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class RunDiagnosticsInfo:
    id: UUID
    team_id: UUID
    conversation_id: UUID
    agent_id: UUID
    agent_version_id: UUID
    status: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    error_code: str | None
    error_message: str | None
    step_count: int
    event_count: int
    usage_input_tokens: int
    usage_output_tokens: int
    usage_total_tokens: int
    usage_cost_amount: Decimal
    steps: tuple[RunDiagnosticStepInfo, ...]


@dataclass(frozen=True, slots=True)
class RunEventInfo:
    id: UUID
    team_id: UUID
    run_id: UUID
    sequence_number: int
    event_type: str
    payload: Mapping[str, object]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RunEventPage:
    items: tuple[RunEventInfo, ...]
    next_cursor: str | None
    has_more: bool
