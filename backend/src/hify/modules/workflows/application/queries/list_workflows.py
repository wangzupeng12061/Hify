from __future__ import annotations

from dataclasses import dataclass

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.workflows.application.authorization import require_read_workflows
from hify.modules.workflows.application.dto import workflow_info_from_domain
from hify.modules.workflows.application.ports import WorkflowsUnitOfWorkFactory
from hify.modules.workflows.contracts.dto import WorkflowInfo


@dataclass(frozen=True, slots=True)
class ListWorkflowsForActorQuery:
    actor: ActorContext


class ListWorkflowsForActorHandler:
    def __init__(self, unit_of_work_factory: WorkflowsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: ListWorkflowsForActorQuery) -> tuple[WorkflowInfo, ...]:
        require_read_workflows(query.actor)
        async with self._unit_of_work_factory() as unit_of_work:
            workflows = await unit_of_work.workflows.list_by_team(team_id=query.actor.team_id)
        return tuple(workflow_info_from_domain(workflow) for workflow in workflows)
