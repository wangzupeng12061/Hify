from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.workflows.application.authorization import require_manage_workflows
from hify.modules.workflows.application.dto import workflow_info_from_domain
from hify.modules.workflows.application.ports import WorkflowsUnitOfWorkFactory
from hify.modules.workflows.contracts.dto import WorkflowInfo
from hify.modules.workflows.domain.errors import WorkflowNotFoundError
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class UpdateWorkflowDraftCommand:
    actor: ActorContext
    workflow_id: UUID
    draft_definition: Mapping[str, object]


class UpdateWorkflowDraftHandler:
    def __init__(
        self,
        unit_of_work_factory: WorkflowsUnitOfWorkFactory,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: UpdateWorkflowDraftCommand) -> WorkflowInfo:
        require_manage_workflows(command.actor)
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            workflow = await unit_of_work.workflows.get_by_id(command.workflow_id)
            if workflow is None or workflow.team_id != command.actor.team_id:
                raise WorkflowNotFoundError("workflow was not found")
            workflow.update_draft(definition=command.draft_definition, now=now)
            await unit_of_work.workflows.save(workflow)
            await unit_of_work.commit()

        return workflow_info_from_domain(workflow)
