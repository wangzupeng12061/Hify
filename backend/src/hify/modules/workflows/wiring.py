from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.providers.contracts.services import ModelCatalog
from hify.modules.tools.contracts.services import ToolCatalog
from hify.modules.workflows.api.dependencies import (
    AuthenticationNotConfiguredAuthenticator,
    RequestAuthenticator,
)
from hify.modules.workflows.api.router import create_workflows_router
from hify.modules.workflows.application.commands.create_workflow import CreateWorkflowHandler
from hify.modules.workflows.application.commands.publish_workflow import PublishWorkflowHandler
from hify.modules.workflows.application.commands.update_workflow_draft import (
    UpdateWorkflowDraftHandler,
)
from hify.modules.workflows.application.queries.get_workflow import (
    GetLatestPublishedWorkflowVersionHandler,
    GetWorkflowForActorHandler,
    GetWorkflowVersionHandler,
    WorkflowCatalogService,
)
from hify.modules.workflows.application.queries.list_workflows import (
    ListWorkflowsForActorHandler,
)
from hify.modules.workflows.application.queries.validate_workflow import (
    ValidateWorkflowDraftHandler,
)
from hify.modules.workflows.contracts.services import WorkflowCatalog
from hify.modules.workflows.infrastructure.database.uow import SqlAlchemyWorkflowsUnitOfWork
from hify.shared.domain.clock import Clock, SystemClock


@dataclass(frozen=True, slots=True)
class WorkflowsModule:
    router: APIRouter
    workflow_catalog: WorkflowCatalog


def create_workflows_module(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    model_catalog: ModelCatalog,
    tool_catalog: ToolCatalog,
    clock: Clock | None = None,
    request_authenticator: RequestAuthenticator | None = None,
) -> WorkflowsModule:
    module_clock = clock or SystemClock()

    def unit_of_work_factory() -> SqlAlchemyWorkflowsUnitOfWork:
        return SqlAlchemyWorkflowsUnitOfWork(session_factory)

    create_workflow_handler = CreateWorkflowHandler(unit_of_work_factory, module_clock)
    update_workflow_draft_handler = UpdateWorkflowDraftHandler(
        unit_of_work_factory,
        module_clock,
    )
    publish_workflow_handler = PublishWorkflowHandler(
        unit_of_work_factory,
        model_catalog,
        tool_catalog,
        module_clock,
    )
    get_workflow_handler = GetWorkflowForActorHandler(unit_of_work_factory)
    list_workflows_handler = ListWorkflowsForActorHandler(unit_of_work_factory)
    validate_workflow_draft_handler = ValidateWorkflowDraftHandler(
        unit_of_work_factory,
        model_catalog,
        tool_catalog,
    )
    get_workflow_version_handler = GetWorkflowVersionHandler(unit_of_work_factory)
    get_latest_published_workflow_version_handler = GetLatestPublishedWorkflowVersionHandler(
        unit_of_work_factory
    )
    workflow_catalog = WorkflowCatalogService(
        get_workflow_version_handler,
        get_latest_published_workflow_version_handler,
    )
    router = create_workflows_router(
        create_workflow_handler=create_workflow_handler,
        update_workflow_draft_handler=update_workflow_draft_handler,
        publish_workflow_handler=publish_workflow_handler,
        get_workflow_handler=get_workflow_handler,
        list_workflows_handler=list_workflows_handler,
        validate_workflow_draft_handler=validate_workflow_draft_handler,
        request_authenticator=request_authenticator or AuthenticationNotConfiguredAuthenticator(),
    )
    return WorkflowsModule(router=router, workflow_catalog=workflow_catalog)
