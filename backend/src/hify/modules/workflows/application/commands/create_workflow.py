from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.workflows.application.authorization import require_manage_workflows
from hify.modules.workflows.application.dto import workflow_info_from_domain
from hify.modules.workflows.application.ports import WorkflowsUnitOfWorkFactory
from hify.modules.workflows.contracts.dto import WorkflowInfo
from hify.modules.workflows.domain.entities import Workflow
from hify.modules.workflows.domain.errors import WorkflowAlreadyExistsError
from hify.modules.workflows.domain.value_objects import normalize_workflow_name
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class CreateWorkflowCommand:
    actor: ActorContext
    name: str
    description: str | None
    draft_definition: Mapping[str, object]


class CreateWorkflowHandler:
    def __init__(
        self,
        unit_of_work_factory: WorkflowsUnitOfWorkFactory,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: CreateWorkflowCommand) -> WorkflowInfo:
        require_manage_workflows(command.actor)
        workflow_name = normalize_workflow_name(command.name)
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            existing_workflow = await unit_of_work.workflows.get_by_team_and_name(
                team_id=command.actor.team_id,
                name=workflow_name,
            )
            if existing_workflow is not None:
                raise WorkflowAlreadyExistsError("workflow already exists")

            workflow = Workflow.create(
                team_id=command.actor.team_id,
                name=workflow_name,
                description=command.description,
                draft_definition=command.draft_definition,
                created_by=command.actor.user_id,
                now=now,
            )
            await unit_of_work.workflows.add(workflow)
            await unit_of_work.commit()

        return workflow_info_from_domain(workflow)
