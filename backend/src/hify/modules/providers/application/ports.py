from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Self

from hify.modules.providers.domain.repositories import (
    ModelProviderRepository,
    ProviderCredentialRepository,
    ProviderModelRepository,
)
from hify.modules.providers.domain.value_objects import CredentialSecret
from hify.shared.application.uow import UnitOfWork


class CredentialEncryptor(Protocol):
    def encrypt(self, plaintext: str) -> CredentialSecret: ...


class ProvidersUnitOfWork(UnitOfWork, Protocol):
    providers: ModelProviderRepository
    credentials: ProviderCredentialRepository
    models: ProviderModelRepository

    async def __aenter__(self) -> Self: ...


ProvidersUnitOfWorkFactory = Callable[[], ProvidersUnitOfWork]
