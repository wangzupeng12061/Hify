from __future__ import annotations

from dataclasses import dataclass

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.providers.application.authorization import require_manage_providers
from hify.modules.providers.application.dto import provider_info_from_domain
from hify.modules.providers.application.ports import CredentialEncryptor, ProvidersUnitOfWorkFactory
from hify.modules.providers.contracts.dto import ProviderInfo
from hify.modules.providers.domain.entities import ModelProvider, ProviderCredential
from hify.modules.providers.domain.errors import ProviderAlreadyExistsError
from hify.modules.providers.domain.value_objects import normalize_provider_name, parse_provider_type
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class CreateProviderCommand:
    actor: ActorContext
    provider_type: str
    name: str
    base_url: str | None
    credential_plaintext: str


class CreateProviderHandler:
    def __init__(
        self,
        unit_of_work_factory: ProvidersUnitOfWorkFactory,
        credential_encryptor: CredentialEncryptor,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._credential_encryptor = credential_encryptor
        self._clock = clock

    async def handle(self, command: CreateProviderCommand) -> ProviderInfo:
        require_manage_providers(command.actor)
        provider_type = parse_provider_type(command.provider_type)
        provider_name = normalize_provider_name(command.name)
        secret = self._credential_encryptor.encrypt(command.credential_plaintext)
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            existing_provider = await unit_of_work.providers.get_by_team_type_and_name(
                team_id=command.actor.team_id,
                provider_type=provider_type,
                name=provider_name,
            )
            if existing_provider is not None:
                raise ProviderAlreadyExistsError("provider already exists")

            provider = ModelProvider.create(
                team_id=command.actor.team_id,
                provider_type=provider_type,
                name=provider_name,
                base_url=command.base_url,
                created_by=command.actor.user_id,
                now=now,
            )
            credential = ProviderCredential.create(
                team_id=command.actor.team_id,
                provider_id=provider.id,
                secret=secret,
                now=now,
            )
            await unit_of_work.providers.add(provider)
            await unit_of_work.credentials.add(credential)
            await unit_of_work.commit()

        return provider_info_from_domain(provider)
