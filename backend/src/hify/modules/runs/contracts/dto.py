from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    error_code: str | None
    error_message: str | None


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
