from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.providers.contracts.services import ModelCatalog
from hify.modules.tools.contracts.services import ToolCatalog
from hify.modules.workflows.application.authorization import require_read_workflows
from hify.modules.workflows.application.dto import workflow_validation_info_from_domain
from hify.modules.workflows.application.ports import WorkflowsUnitOfWorkFactory
from hify.modules.workflows.contracts.dto import WorkflowValidationInfo
from hify.modules.workflows.domain.errors import WorkflowNotFoundError
from hify.modules.workflows.domain.value_objects import (
    WorkflowDefinitionIssue,
    WorkflowDefinitionValidation,
    collect_model_ids,
    collect_tool_ids,
    validate_workflow_definition,
)
from hify.shared.domain.errors import HifyError


@dataclass(frozen=True, slots=True)
class ValidateWorkflowDraftQuery:
    actor: ActorContext
    workflow_id: UUID


class ValidateWorkflowDraftHandler:
    def __init__(
        self,
        unit_of_work_factory: WorkflowsUnitOfWorkFactory,
        model_catalog: ModelCatalog,
        tool_catalog: ToolCatalog,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._model_catalog = model_catalog
        self._tool_catalog = tool_catalog

    async def handle(self, query: ValidateWorkflowDraftQuery) -> WorkflowValidationInfo:
        require_read_workflows(query.actor)
        async with self._unit_of_work_factory() as unit_of_work:
            workflow = await unit_of_work.workflows.get_by_id(query.workflow_id)
        if workflow is None or workflow.team_id != query.actor.team_id:
            raise WorkflowNotFoundError("workflow was not found")

        validation = validate_workflow_definition(workflow.draft_definition)
        issues = list(validation.issues)
        if validation.is_valid:
            issues.extend(
                await self._validate_references(
                    team_id=query.actor.team_id,
                    definition=workflow.draft_definition,
                )
            )
        return workflow_validation_info_from_domain(
            WorkflowDefinitionValidation(issues=tuple(issues))
        )

    async def _validate_references(
        self,
        *,
        team_id: UUID,
        definition: object,
    ) -> tuple[WorkflowDefinitionIssue, ...]:
        if not isinstance(definition, dict):
            return ()
        issues: list[WorkflowDefinitionIssue] = []
        for model_id in collect_model_ids(definition):
            try:
                await self._model_catalog.get_model(team_id=team_id, model_id=model_id)
            except HifyError:
                issues.append(
                    WorkflowDefinitionIssue(
                        code="unknown_model",
                        path="$.nodes",
                        message=f"model {model_id} was not found",
                    )
                )
        for tool_id in collect_tool_ids(definition):
            try:
                await self._tool_catalog.get_tool(team_id=team_id, tool_id=tool_id)
            except HifyError:
                issues.append(
                    WorkflowDefinitionIssue(
                        code="unknown_tool",
                        path="$.nodes",
                        message=f"tool {tool_id} was not found",
                    )
                )
        return tuple(issues)
