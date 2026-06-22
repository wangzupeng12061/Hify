from __future__ import annotations

from datetime import datetime
from typing import Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    queue: str
    job_kind: str
    status: str
    idempotency_key: str
    payload: Mapping[str, object]
    attempt_count: int
    max_attempts: int
    available_at: datetime
    lease_owner: str | None
    lease_expires_at: datetime | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
