from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from hify.bootstrap.settings import Settings
from hify.modules.identity.wiring import IdentityModule, create_identity_module
from hify.modules.providers.wiring import ProvidersModule, create_providers_module
from hify.shared.infrastructure.database import create_engine, create_session_factory


@dataclass(frozen=True, slots=True)
class HifyContainer:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    identity: IdentityModule
    providers: ProvidersModule


def create_container(settings: Settings | None = None) -> HifyContainer:
    resolved_settings = settings or Settings()
    engine = create_engine(
        resolved_settings.database_url,
        echo=resolved_settings.database_echo,
    )
    session_factory = create_session_factory(engine)
    identity = create_identity_module(session_factory)
    providers = create_providers_module(
        session_factory,
        credential_encryption_key=resolved_settings.provider_credential_encryption_key,
        credential_key_version=resolved_settings.provider_credential_key_version,
    )
    return HifyContainer(
        settings=resolved_settings,
        engine=engine,
        session_factory=session_factory,
        identity=identity,
        providers=providers,
    )
