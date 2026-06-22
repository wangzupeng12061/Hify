from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.providers.contracts.services import ModelCatalog
from hify.modules.tools.contracts.services import ToolCatalog
from hify.modules.workflows.application.authorization import require_manage_workflows
from hify.modules.workflows.application.dto import workflow_version_info_from_domain
from hify.modules.workflows.application.ports import WorkflowsUnitOfWorkFactory
from hify.modules.workflows.contracts.dto import WorkflowVersionInfo
from hify.modules.workflows.domain.errors import WorkflowNotFoundError, WorkflowValidationError
from hify.modules.workflows.domain.value_objects import (
    collect_model_ids,
    collect_tool_ids,
    validate_workflow_definition,
)
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class PublishWorkflowCommand:
    actor: ActorContext
    workflow_id: UUID


class PublishWorkflowHandler:
    def __init__(
        self,
        unit_of_work_factory: WorkflowsUnitOfWorkFactory,
        model_catalog: ModelCatalog,
        tool_catalog: ToolCatalog,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._model_catalog = model_catalog
        self._tool_catalog = tool_catalog
        self._clock = clock

    async def handle(self, command: PublishWorkflowCommand) -> WorkflowVersionInfo:
        require_manage_workflows(command.actor)
        async with self._unit_of_work_factory() as unit_of_work:
            workflow = await unit_of_work.workflows.get_by_id(command.workflow_id)
            if workflow is None or workflow.team_id != command.actor.team_id:
                raise WorkflowNotFoundError("workflow was not found")

            validation = validate_workflow_definition(workflow.draft_definition)
            if not validation.is_valid:
                raise WorkflowValidationError(
                    "workflow definition is invalid",
                    metadata={"issues": tuple(issue.code for issue in validation.issues)},
                )
            await self._validate_references(
                team_id=command.actor.team_id,
                definition=workflow.draft_definition,
            )

            workflow_version = workflow.publish(
                published_by=command.actor.user_id,
                now=self._clock.now(),
            )
            await unit_of_work.workflows.save(workflow)
            await unit_of_work.versions.add(workflow_version)
            await unit_of_work.commit()

        return workflow_version_info_from_domain(workflow_version)

    async def _validate_references(self, *, team_id: UUID, definition: object) -> None:
        if not isinstance(definition, dict):
            return
        for model_id in collect_model_ids(definition):
            await self._model_catalog.get_model(team_id=team_id, model_id=model_id)
        for tool_id in collect_tool_ids(definition):
            await self._tool_catalog.get_tool(team_id=team_id, tool_id=tool_id)
