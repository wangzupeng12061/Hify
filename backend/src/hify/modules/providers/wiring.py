from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.providers.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.providers.api.router import create_providers_router
from hify.modules.providers.application.commands.add_provider_model import AddProviderModelHandler
from hify.modules.providers.application.commands.create_provider import CreateProviderHandler
from hify.modules.providers.application.queries.get_model import (
    GetModelHandler,
    ListModelsHandler,
    ModelCatalogService,
)
from hify.modules.providers.contracts.services import ModelCatalog
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
    get_model_handler = GetModelHandler(unit_of_work_factory)
    list_models_handler = ListModelsHandler(unit_of_work_factory)
    model_catalog = ModelCatalogService(get_model_handler, list_models_handler)

    router = create_providers_router(
        create_provider_handler=create_provider_handler,
        add_provider_model_handler=add_provider_model_handler,
        request_authenticator=AuthenticationNotConfiguredAuthenticator(),
    )
    return ProvidersModule(router=router, model_catalog=model_catalog)
