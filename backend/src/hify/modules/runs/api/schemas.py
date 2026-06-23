from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateRunRequest(BaseModel):
    conversation_id: UUID
    idempotency_key: str = Field(min_length=1, max_length=120)


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class RunDiagnosticStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class RunDiagnosticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    steps: tuple[RunDiagnosticStepResponse, ...]


class RunEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    run_id: UUID
    sequence_number: int
    event_type: str
    payload: Mapping[str, object]
    created_at: datetime


class RunEventPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: tuple[RunEventResponse, ...]
    next_cursor: str | None
    has_more: bool
