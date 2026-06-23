from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.usage.api.dependencies import RequestAuthenticator
from hify.modules.usage.api.schemas import (
    SetUsageQuotaRequest,
    UsageCostByDayResponse,
    UsageCostByModelResponse,
    UsageCostSummaryResponse,
    UsageQuotaResponse,
    UsageQuotaStatusResponse,
    UsageSummaryResponse,
)
from hify.modules.usage.application.commands.set_team_usage_quota import (
    SetTeamUsageQuotaCommand,
    SetTeamUsageQuotaHandler,
)
from hify.modules.usage.application.queries.get_team_usage_quota_status import (
    GetTeamUsageQuotaStatusHandler,
    GetTeamUsageQuotaStatusQuery,
)
from hify.modules.usage.application.queries.get_run_usage_summary import (
    GetRunUsageSummaryHandler,
    GetRunUsageSummaryQuery,
)
from hify.modules.usage.application.queries.get_usage_cost_by_day import (
    GetUsageCostByDayHandler,
    GetUsageCostByDayQuery,
)
from hify.modules.usage.application.queries.get_usage_cost_by_model import (
    GetUsageCostByModelHandler,
    GetUsageCostByModelQuery,
)
from hify.modules.usage.application.queries.get_usage_cost_summary import (
    GetUsageCostSummaryHandler,
    GetUsageCostSummaryQuery,
)
from hify.modules.usage.application.queries.get_team_usage_summary import (
    GetTeamUsageSummaryHandler,
    GetTeamUsageSummaryQuery,
)
from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, PermissionDeniedError


def create_usage_router(
    *,
    get_team_summary_handler: GetTeamUsageSummaryHandler,
    get_run_summary_handler: GetRunUsageSummaryHandler,
    get_quota_status_handler: GetTeamUsageQuotaStatusHandler,
    get_cost_summary_handler: GetUsageCostSummaryHandler,
    get_cost_by_model_handler: GetUsageCostByModelHandler,
    get_cost_by_day_handler: GetUsageCostByDayHandler,
    set_quota_handler: SetTeamUsageQuotaHandler,
    request_authenticator: RequestAuthenticator,
) -> APIRouter:
    router = APIRouter(prefix="/usage", tags=["usage"])

    async def get_current_actor(request: Request) -> ActorContext:
        try:
            return await request_authenticator.authenticate(request)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/summary", response_model=UsageSummaryResponse)
    async def get_team_usage_summary(
        actor: ActorContext = Depends(get_current_actor),
    ) -> UsageSummaryResponse:
        try:
            summary = await get_team_summary_handler.handle(
                GetTeamUsageSummaryQuery(actor=actor)
            )
            return UsageSummaryResponse.model_validate(summary)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/quota", response_model=UsageQuotaStatusResponse)
    async def get_team_usage_quota_status(
        actor: ActorContext = Depends(get_current_actor),
    ) -> UsageQuotaStatusResponse:
        try:
            status_info = await get_quota_status_handler.handle(
                GetTeamUsageQuotaStatusQuery(actor=actor)
            )
            return UsageQuotaStatusResponse.model_validate(status_info)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/cost-summary", response_model=UsageCostSummaryResponse)
    async def get_usage_cost_summary(
        period_start: datetime | None = Query(default=None, alias="from"),
        period_end: datetime | None = Query(default=None, alias="to"),
        actor: ActorContext = Depends(get_current_actor),
    ) -> UsageCostSummaryResponse:
        try:
            summary = await get_cost_summary_handler.handle(
                GetUsageCostSummaryQuery(
                    actor=actor,
                    period_start=period_start,
                    period_end=period_end,
                )
            )
            return UsageCostSummaryResponse.model_validate(summary)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/cost-by-model", response_model=UsageCostByModelResponse)
    async def get_usage_cost_by_model(
        period_start: datetime | None = Query(default=None, alias="from"),
        period_end: datetime | None = Query(default=None, alias="to"),
        actor: ActorContext = Depends(get_current_actor),
    ) -> UsageCostByModelResponse:
        try:
            cost_by_model = await get_cost_by_model_handler.handle(
                GetUsageCostByModelQuery(
                    actor=actor,
                    period_start=period_start,
                    period_end=period_end,
                )
            )
            return UsageCostByModelResponse.model_validate(cost_by_model)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/cost-by-day", response_model=UsageCostByDayResponse)
    async def get_usage_cost_by_day(
        period_start: datetime | None = Query(default=None, alias="from"),
        period_end: datetime | None = Query(default=None, alias="to"),
        actor: ActorContext = Depends(get_current_actor),
    ) -> UsageCostByDayResponse:
        try:
            cost_by_day = await get_cost_by_day_handler.handle(
                GetUsageCostByDayQuery(
                    actor=actor,
                    period_start=period_start,
                    period_end=period_end,
                )
            )
            return UsageCostByDayResponse.model_validate(cost_by_day)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.put("/quota", response_model=UsageQuotaResponse)
    async def set_team_usage_quota(
        request: SetUsageQuotaRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> UsageQuotaResponse:
        try:
            quota = await set_quota_handler.handle(
                SetTeamUsageQuotaCommand(
                    actor=actor,
                    monthly_token_limit=request.monthly_token_limit,
                )
            )
            return UsageQuotaResponse.model_validate(quota)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/runs/{run_id}/summary", response_model=UsageSummaryResponse)
    async def get_run_usage_summary(
        run_id: UUID,
        actor: ActorContext = Depends(get_current_actor),
    ) -> UsageSummaryResponse:
        try:
            summary = await get_run_summary_handler.handle(
                GetRunUsageSummaryQuery(actor=actor, run_id=run_id)
            )
            return UsageSummaryResponse.model_validate(summary)
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
