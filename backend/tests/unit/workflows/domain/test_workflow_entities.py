from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from hify.modules.workflows.domain.entities import Workflow
from hify.modules.workflows.domain.value_objects import (
    WorkflowStatus,
    default_workflow_definition,
    validate_workflow_definition,
)


def test_workflow_publish_creates_version_and_marks_published() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)
    workflow = Workflow.create(
        team_id=UUID("00000000-0000-7000-8000-000000000001"),
        name=" Support Flow ",
        description=" Answers questions ",
        draft_definition=default_workflow_definition(),
        created_by=UUID("00000000-0000-7000-8000-000000000002"),
        now=now,
    )

    workflow_version = workflow.publish(
        published_by=UUID("00000000-0000-7000-8000-000000000002"),
        now=now,
    )

    assert workflow.status is WorkflowStatus.PUBLISHED
    assert workflow.latest_version_number == 1
    assert workflow.version == 1
    assert workflow_version.version_number == 1
    assert workflow_version.definition == default_workflow_definition()


def test_validate_workflow_definition_requires_reachable_end() -> None:
    definition = {
        "nodes": [
            {"id": "start", "kind": "start", "config": {}},
            {"id": "llm", "kind": "llm", "config": {"provider_model_id": "not-a-uuid"}},
            {"id": "end", "kind": "end", "config": {}},
        ],
        "edges": [{"source_node_id": "start", "target_node_id": "llm"}],
    }

    validation = validate_workflow_definition(definition)

    assert not validation.is_valid
    assert {issue.code for issue in validation.issues} >= {
        "invalid_node_reference",
        "dead_end_node",
    }
