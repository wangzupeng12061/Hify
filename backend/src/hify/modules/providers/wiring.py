from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.providers.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.providers.api.router import create_providers_router
from hify.modules.providers.application.commands.add_provider_model import AddProviderModelHandler
from hify.modules.providers.application.commands.create_provider import CreateProviderHandler
from hify.modules.providers.application.commands.set_provider_model_pricing import (
    SetProviderModelPricingHandler,
)
from hify.modules.providers.application.queries.get_model import (
    GetModelPricingHandler,
    GetModelHandler,
    ListModelsHandler,
    ModelCatalogService,
    ModelPricingCatalogService,
)
from hify.modules.providers.contracts.services import (
    EmbeddingGateway,
    ModelCatalog,
    ModelGateway,
    ModelPricingCatalog,
)
from hify.modules.providers.infrastructure.adapters.fake import MissingEmbeddingGateway, MissingModelGateway
from hify.modules.providers.infrastructure.database.uow import SqlAlchemyProvidersUnitOfWork
from hify.modules.providers.infrastructure.encryption import (
    FernetCredentialEncryptor,
    MissingCredentialEncryptor,
)
from hify.shared.domain.clock import Clock, SystemClock


@dataclass(frozen=True, slots=True)
class ProvidersModule:
    router: APIRouter
    model_catalog: ModelCatalog
    model_pricing_catalog: ModelPricingCatalog
    model_gateway: ModelGateway
    embedding_gateway: EmbeddingGateway


def create_providers_module(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    credential_encryption_key: str | None,
    credential_key_version: int = 1,
    clock: Clock | None = None,
) -> ProvidersModule:
    module_clock = clock or SystemClock()
    credential_encryptor = (
        FernetCredentialEncryptor(credential_encryption_key, key_version=credential_key_version)
        if credential_encryption_key
        else MissingCredentialEncryptor()
    )

    def unit_of_work_factory() -> SqlAlchemyProvidersUnitOfWork:
        return SqlAlchemyProvidersUnitOfWork(session_factory)

    create_provider_handler = CreateProviderHandler(
        unit_of_work_factory,
        credential_encryptor,
        module_clock,
    )
    add_provider_model_handler = AddProviderModelHandler(unit_of_work_factory, module_clock)
    set_provider_model_pricing_handler = SetProviderModelPricingHandler(
        unit_of_work_factory,
        module_clock,
    )
    get_model_handler = GetModelHandler(unit_of_work_factory)
    list_models_handler = ListModelsHandler(unit_of_work_factory)
    get_model_pricing_handler = GetModelPricingHandler(unit_of_work_factory)
    model_catalog = ModelCatalogService(get_model_handler, list_models_handler)
    model_pricing_catalog = ModelPricingCatalogService(get_model_pricing_handler)
    model_gateway = MissingModelGateway()
    embedding_gateway = MissingEmbeddingGateway()

    router = create_providers_router(
        create_provider_handler=create_provider_handler,
        add_provider_model_handler=add_provider_model_handler,
        set_provider_model_pricing_handler=set_provider_model_pricing_handler,
        request_authenticator=AuthenticationNotConfiguredAuthenticator(),
    )
    return ProvidersModule(
        router=router,
        model_catalog=model_catalog,
        model_pricing_catalog=model_pricing_catalog,
        model_gateway=model_gateway,
        embedding_gateway=embedding_gateway,
    )
