from __future__ import annotations

from hify.modules.agents.domain.value_objects import WorkflowBindingSnapshot
from hify.modules.workflows.contracts.dto import WorkflowVersionInfo


def workflow_binding_snapshot_from_workflow_version(
    workflow_version: WorkflowVersionInfo,
) -> WorkflowBindingSnapshot:
    return WorkflowBindingSnapshot(
        workflow_id=workflow_version.workflow_id,
        workflow_version_id=workflow_version.id,
        workflow_version_number=workflow_version.version_number,
        workflow_name=workflow_version.name,
        workflow_definition=dict(workflow_version.definition),
    )
