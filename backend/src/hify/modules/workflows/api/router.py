from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.workflows.api.dependencies import RequestAuthenticator
from hify.modules.workflows.api.schemas import (
    CreateWorkflowRequest,
    UpdateWorkflowDraftRequest,
    WorkflowResponse,
    WorkflowValidationResponse,
    WorkflowVersionResponse,
)
from hify.modules.workflows.application.commands.create_workflow import (
    CreateWorkflowCommand,
    CreateWorkflowHandler,
)
from hify.modules.workflows.application.commands.publish_workflow import (
    PublishWorkflowCommand,
    PublishWorkflowHandler,
)
from hify.modules.workflows.application.commands.update_workflow_draft import (
    UpdateWorkflowDraftCommand,
    UpdateWorkflowDraftHandler,
)
from hify.modules.workflows.application.queries.get_workflow import (
    GetWorkflowForActorHandler,
    GetWorkflowForActorQuery,
)
from hify.modules.workflows.application.queries.validate_workflow import (
    ValidateWorkflowDraftHandler,
    ValidateWorkflowDraftQuery,
)
from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, PermissionDeniedError


def create_workflows_router(
    *,
    create_workflow_handler: CreateWorkflowHandler,
    update_workflow_draft_handler: UpdateWorkflowDraftHandler,
    publish_workflow_handler: PublishWorkflowHandler,
    get_workflow_handler: GetWorkflowForActorHandler,
    validate_workflow_draft_handler: ValidateWorkflowDraftHandler,
    request_authenticator: RequestAuthenticator,
) -> APIRouter:
    router = APIRouter(prefix="/workflows", tags=["workflows"])

    async def get_current_actor(request: Request) -> ActorContext:
        try:
            return await request_authenticator.authenticate(request)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
    async def create_workflow(
        request: CreateWorkflowRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> WorkflowResponse:
        try:
            command = CreateWorkflowCommand(
                actor=actor,
                name=request.name,
                description=request.description,
                draft_definition=request.draft_definition,
            )
            workflow = await create_workflow_handler.handle(command)
            return WorkflowResponse.model_validate(workflow)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/{workflow_id}", response_model=WorkflowResponse)
    async def get_workflow(
        workflow_id: UUID,
        actor: ActorContext = Depends(get_current_actor),
    ) -> WorkflowResponse:
        try:
            workflow = await get_workflow_handler.handle(
                GetWorkflowForActorQuery(actor=actor, workflow_id=workflow_id)
            )
            return WorkflowResponse.model_validate(workflow)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.put("/{workflow_id}/draft", response_model=WorkflowResponse)
    async def update_workflow_draft(
        workflow_id: UUID,
        request: UpdateWorkflowDraftRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> WorkflowResponse:
        try:
            command = UpdateWorkflowDraftCommand(
                actor=actor,
                workflow_id=workflow_id,
                draft_definition=request.draft_definition,
            )
            workflow = await update_workflow_draft_handler.handle(command)
            return WorkflowResponse.model_validate(workflow)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post("/{workflow_id}/validate", response_model=WorkflowValidationResponse)
    async def validate_workflow_draft(
        workflow_id: UUID,
        actor: ActorContext = Depends(get_current_actor),
    ) -> WorkflowValidationResponse:
        try:
            validation = await validate_workflow_draft_handler.handle(
                ValidateWorkflowDraftQuery(actor=actor, workflow_id=workflow_id)
            )
            return WorkflowValidationResponse.model_validate(validation)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post(
        "/{workflow_id}/publish",
        response_model=WorkflowVersionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def publish_workflow(
        workflow_id: UUID,
        actor: ActorContext = Depends(get_current_actor),
    ) -> WorkflowVersionResponse:
        try:
            workflow_version = await publish_workflow_handler.handle(
                PublishWorkflowCommand(actor=actor, workflow_id=workflow_id)
            )
            return WorkflowVersionResponse.model_validate(workflow_version)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    return router


def _to_http_error(error: HifyError) -> HTTPException:
    if isinstance(error, PermissionDeniedError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(error, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, ConflictError):
        status_code = status.HTTP_409_CONFLICT
    else:
        status_code = status.HTTP_400_BAD_REQUEST

    detail = error.to_detail()
    return HTTPException(
        status_code=status_code,
        detail={
            "code": detail.code,
            "message": detail.message,
            "metadata": detail.metadata,
        },
    )
