from __future__ import annotations

from hify.modules.workflows.contracts.dto import (
    WorkflowInfo,
    WorkflowValidationInfo,
    WorkflowValidationIssueInfo,
    WorkflowVersionInfo,
)
from hify.modules.workflows.domain.entities import Workflow, WorkflowVersion
from hify.modules.workflows.domain.value_objects import WorkflowDefinitionValidation


def workflow_info_from_domain(workflow: Workflow) -> WorkflowInfo:
    return WorkflowInfo(
        id=workflow.id,
        team_id=workflow.team_id,
        name=workflow.name,
        description=workflow.description,
        status=workflow.status.value,
        draft_definition=workflow.draft_definition,
        latest_version_number=workflow.latest_version_number,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


def workflow_version_info_from_domain(workflow_version: WorkflowVersion) -> WorkflowVersionInfo:
    return WorkflowVersionInfo(
        id=workflow_version.id,
        team_id=workflow_version.team_id,
        workflow_id=workflow_version.workflow_id,
        version_number=workflow_version.version_number,
        name=workflow_version.name,
        description=workflow_version.description,
        definition=workflow_version.definition,
        created_at=workflow_version.created_at,
    )


def workflow_validation_info_from_domain(
    validation: WorkflowDefinitionValidation,
) -> WorkflowValidationInfo:
    return WorkflowValidationInfo(
        is_valid=validation.is_valid,
        issues=tuple(
            WorkflowValidationIssueInfo(
                code=issue.code,
                path=issue.path,
                message=issue.message,
            )
            for issue in validation.issues
        ),
    )
