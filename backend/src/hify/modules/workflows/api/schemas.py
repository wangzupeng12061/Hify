from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


def _default_workflow_definition() -> dict[str, Any]:
    return {
        "nodes": [
            {"id": "start", "kind": "start", "config": {}},
            {"id": "end", "kind": "end", "config": {}},
        ],
        "edges": [{"source_node_id": "start", "target_node_id": "end"}],
    }


class CreateWorkflowRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    draft_definition: dict[str, Any] = Field(default_factory=_default_workflow_definition)


class UpdateWorkflowDraftRequest(BaseModel):
    draft_definition: dict[str, Any]


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    name: str
    description: str | None
    status: str
    draft_definition: dict[str, Any]
    latest_version_number: int
    created_at: datetime
    updated_at: datetime


class WorkflowVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    workflow_id: UUID
    version_number: int
    name: str
    description: str | None
    definition: dict[str, Any]
    created_at: datetime


class WorkflowValidationIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    path: str
    message: str


class WorkflowValidationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_valid: bool
    issues: tuple[WorkflowValidationIssueResponse, ...]
