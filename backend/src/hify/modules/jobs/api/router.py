from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.jobs.api.dependencies import RequestAuthenticator
from hify.modules.jobs.api.schemas import JobResponse
from hify.modules.jobs.application.queries.get_job import GetJobForActorHandler, GetJobForActorQuery
from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, PermissionDeniedError


def create_jobs_router(
    *,
    get_job_handler: GetJobForActorHandler,
    request_authenticator: RequestAuthenticator,
) -> APIRouter:
    router = APIRouter(prefix="/jobs", tags=["jobs"])

    async def get_current_actor(request: Request) -> ActorContext:
        try:
            return await request_authenticator.authenticate(request)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/{job_id}", response_model=JobResponse)
    async def get_job(
        job_id: UUID,
        actor: ActorContext = Depends(get_current_actor),
    ) -> JobResponse:
        try:
            job = await get_job_handler.handle(GetJobForActorQuery(actor=actor, job_id=job_id))
            return JobResponse.model_validate(job)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    return router


def _to_http_error(error: HifyError) -> HTTPException:
    detail = error.to_detail()
    if isinstance(error, PermissionDeniedError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(error, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, ConflictError):
        status_code = status.HTTP_409_CONFLICT
    else:
        status_code = status.HTTP_400_BAD_REQUEST
    return HTTPException(
        status_code=status_code,
        detail={
            "code": detail.code,
            "message": detail.message,
            "metadata": detail.metadata,
        },
    )
