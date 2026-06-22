from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.workflows.application.authorization import require_read_workflows
from hify.modules.workflows.application.dto import (
    workflow_info_from_domain,
    workflow_version_info_from_domain,
)
from hify.modules.workflows.application.ports import WorkflowsUnitOfWorkFactory
from hify.modules.workflows.contracts.dto import WorkflowInfo, WorkflowVersionInfo
from hify.modules.workflows.contracts.services import WorkflowCatalog
from hify.modules.workflows.domain.errors import WorkflowNotFoundError, WorkflowVersionNotFoundError


@dataclass(frozen=True, slots=True)
class GetWorkflowForActorQuery:
    actor: ActorContext
    workflow_id: UUID


@dataclass(frozen=True, slots=True)
class GetWorkflowVersionQuery:
    team_id: UUID
    workflow_version_id: UUID


@dataclass(frozen=True, slots=True)
class GetLatestPublishedWorkflowVersionQuery:
    team_id: UUID
    workflow_id: UUID


class GetWorkflowForActorHandler:
    def __init__(self, unit_of_work_factory: WorkflowsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetWorkflowForActorQuery) -> WorkflowInfo:
        require_read_workflows(query.actor)
        async with self._unit_of_work_factory() as unit_of_work:
            workflow = await unit_of_work.workflows.get_by_id(query.workflow_id)
        if workflow is None or workflow.team_id != query.actor.team_id:
            raise WorkflowNotFoundError("workflow was not found")
        return workflow_info_from_domain(workflow)


class GetWorkflowVersionHandler:
    def __init__(self, unit_of_work_factory: WorkflowsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetWorkflowVersionQuery) -> WorkflowVersionInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            workflow_version = await unit_of_work.versions.get_by_id(query.workflow_version_id)
        if workflow_version is None or workflow_version.team_id != query.team_id:
            raise WorkflowVersionNotFoundError("workflow version was not found")
        return workflow_version_info_from_domain(workflow_version)


class GetLatestPublishedWorkflowVersionHandler:
    def __init__(self, unit_of_work_factory: WorkflowsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetLatestPublishedWorkflowVersionQuery) -> WorkflowVersionInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            workflow = await unit_of_work.workflows.get_by_id(query.workflow_id)
            if workflow is None or workflow.team_id != query.team_id:
                raise WorkflowNotFoundError("workflow was not found")
            workflow_version = await unit_of_work.versions.get_latest_by_workflow_id(workflow.id)
        if workflow_version is None:
            raise WorkflowVersionNotFoundError("workflow version was not found")
        return workflow_version_info_from_domain(workflow_version)


class WorkflowCatalogService(WorkflowCatalog):
    def __init__(
        self,
        get_workflow_version_handler: GetWorkflowVersionHandler,
        get_latest_published_workflow_version_handler: GetLatestPublishedWorkflowVersionHandler,
    ) -> None:
        self._get_workflow_version_handler = get_workflow_version_handler
        self._get_latest_published_workflow_version_handler = (
            get_latest_published_workflow_version_handler
        )

    async def get_latest_published_version(
        self,
        *,
        team_id: UUID,
        workflow_id: UUID,
    ) -> WorkflowVersionInfo:
        return await self._get_latest_published_workflow_version_handler.handle(
            GetLatestPublishedWorkflowVersionQuery(team_id=team_id, workflow_id=workflow_id)
        )

    async def get_workflow_version(
        self,
        *,
        team_id: UUID,
        workflow_version_id: UUID,
    ) -> WorkflowVersionInfo:
        return await self._get_workflow_version_handler.handle(
            GetWorkflowVersionQuery(
                team_id=team_id,
                workflow_version_id=workflow_version_id,
            )
        )
