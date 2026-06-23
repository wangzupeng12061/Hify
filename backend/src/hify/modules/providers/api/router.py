from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.providers.api.dependencies import RequestAuthenticator
from hify.modules.providers.api.schemas import (
    AddProviderModelRequest,
    CreateProviderRequest,
    ModelResponse,
    ProviderResponse,
    SetProviderModelPricingRequest,
)
from hify.modules.providers.application.commands.add_provider_model import (
    AddProviderModelCommand,
    AddProviderModelHandler,
)
from hify.modules.providers.application.commands.create_provider import (
    CreateProviderCommand,
    CreateProviderHandler,
)
from hify.modules.providers.application.commands.set_provider_model_pricing import (
    SetProviderModelPricingCommand,
    SetProviderModelPricingHandler,
)
from hify.modules.providers.application.queries.list_models import (
    ListModelsForActorHandler,
    ListModelsForActorQuery,
)
from hify.modules.providers.contracts.dto import ModelInfo
from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, PermissionDeniedError


def create_providers_router(
    *,
    create_provider_handler: CreateProviderHandler,
    add_provider_model_handler: AddProviderModelHandler,
    set_provider_model_pricing_handler: SetProviderModelPricingHandler,
    list_models_handler: ListModelsForActorHandler,
    request_authenticator: RequestAuthenticator,
) -> APIRouter:
    router = APIRouter(prefix="/providers", tags=["providers"])

    async def get_current_actor(request: Request) -> ActorContext:
        try:
            return await request_authenticator.authenticate(request)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
    async def create_provider(
        request: CreateProviderRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> ProviderResponse:
        try:
            command = CreateProviderCommand(
                actor=actor,
                provider_type=request.provider_type,
                name=request.name,
                base_url=request.base_url,
                credential_plaintext=request.credential_plaintext,
            )
            provider = await create_provider_handler.handle(command)
            return ProviderResponse(
                id=provider.id,
                team_id=provider.team_id,
                provider_type=provider.provider_type,
                name=provider.name,
                base_url=provider.base_url,
                status=provider.status,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/models", response_model=tuple[ModelResponse, ...])
    async def list_provider_models(
        actor: ActorContext = Depends(get_current_actor),
    ) -> tuple[ModelResponse, ...]:
        try:
            models = await list_models_handler.handle(ListModelsForActorQuery(actor=actor))
            return tuple(_model_response(model) for model in models)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post(
        "/{provider_id}/models",
        response_model=ModelResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def add_provider_model(
        provider_id: UUID,
        request: AddProviderModelRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> ModelResponse:
        try:
            command = AddProviderModelCommand(
                actor=actor,
                provider_id=provider_id,
                model_name=request.model_name,
                display_name=request.display_name,
                kind=request.kind,
                context_window_tokens=request.context_window_tokens,
                supports_tools=request.supports_tools,
                supports_vision=request.supports_vision,
                supports_structured_output=request.supports_structured_output,
            )
            model = await add_provider_model_handler.handle(command)
            return _model_response(model)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.put(
        "/models/{model_id}/pricing",
        response_model=ModelResponse,
    )
    async def set_provider_model_pricing(
        model_id: UUID,
        request: SetProviderModelPricingRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> ModelResponse:
        try:
            command = SetProviderModelPricingCommand(
                actor=actor,
                model_id=model_id,
                price_per_1m_input_tokens=request.price_per_1m_input_tokens,
                price_per_1m_output_tokens=request.price_per_1m_output_tokens,
            )
            model = await set_provider_model_pricing_handler.handle(command)
            return _model_response(model)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    return router


def _model_response(model: ModelInfo) -> ModelResponse:
    return ModelResponse.model_validate(model, from_attributes=True)


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
