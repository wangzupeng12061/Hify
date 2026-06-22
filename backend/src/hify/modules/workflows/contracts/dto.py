from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WorkflowInfo:
    id: UUID
    team_id: UUID
    name: str
    description: str | None
    status: str
    draft_definition: Mapping[str, object]
    latest_version_number: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class WorkflowVersionInfo:
    id: UUID
    team_id: UUID
    workflow_id: UUID
    version_number: int
    name: str
    description: str | None
    definition: Mapping[str, object]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class WorkflowValidationIssueInfo:
    code: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class WorkflowValidationInfo:
    is_valid: bool
    issues: tuple[WorkflowValidationIssueInfo, ...]
