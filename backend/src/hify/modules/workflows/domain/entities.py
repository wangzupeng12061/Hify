from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from uuid import UUID

from hify.modules.workflows.domain.errors import WorkflowValidationError
from hify.modules.workflows.domain.value_objects import (
    WorkflowStatus,
    normalize_workflow_definition,
    normalize_workflow_description,
    normalize_workflow_name,
    validate_workflow_definition,
)
from hify.shared.domain.ids import new_uuid


@dataclass(slots=True)
class Workflow:
    id: UUID
    team_id: UUID
    name: str
    description: str | None
    status: WorkflowStatus
    draft_definition: Mapping[str, object]
    latest_version_number: int
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        name: str,
        description: str | None,
        draft_definition: Mapping[str, object],
        created_by: UUID,
        now: datetime,
    ) -> Workflow:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            name=normalize_workflow_name(name),
            description=normalize_workflow_description(description),
            status=WorkflowStatus.DRAFT,
            draft_definition=normalize_workflow_definition(draft_definition),
            latest_version_number=0,
            version=0,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

    def update_draft(
        self,
        *,
        definition: Mapping[str, object],
        now: datetime,
    ) -> None:
        self.draft_definition = normalize_workflow_definition(definition)
        self._mark_updated(now)

    def publish(self, *, published_by: UUID, now: datetime) -> WorkflowVersion:
        validation = validate_workflow_definition(self.draft_definition)
        if not validation.is_valid:
            raise WorkflowValidationError(
                "workflow definition is invalid",
                metadata={"issues": tuple(issue.code for issue in validation.issues)},
            )
        next_version_number = self.latest_version_number + 1
        self.latest_version_number = next_version_number
        self.status = WorkflowStatus.PUBLISHED
        self._mark_updated(now)
        return WorkflowVersion.create(
            team_id=self.team_id,
            workflow_id=self.id,
            version_number=next_version_number,
            name=self.name,
            description=self.description,
            definition=self.draft_definition,
            published_by=published_by,
            now=now,
        )

    def _mark_updated(self, now: datetime) -> None:
        self.version += 1
        self.updated_at = now


@dataclass(slots=True)
class WorkflowVersion:
    id: UUID
    team_id: UUID
    workflow_id: UUID
    version_number: int
    name: str
    description: str | None
    definition: Mapping[str, object]
    published_by: UUID
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        workflow_id: UUID,
        version_number: int,
        name: str,
        description: str | None,
        definition: Mapping[str, object],
        published_by: UUID,
        now: datetime,
    ) -> WorkflowVersion:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            workflow_id=workflow_id,
            version_number=version_number,
            name=normalize_workflow_name(name),
            description=normalize_workflow_description(description),
            definition=normalize_workflow_definition(definition),
            published_by=published_by,
            created_at=now,
        )
