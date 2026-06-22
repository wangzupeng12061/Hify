from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from hify.bootstrap.settings import Settings
from hify.modules.identity.wiring import IdentityModule, create_identity_module
from hify.shared.infrastructure.database import create_engine, create_session_factory


@dataclass(frozen=True, slots=True)
class HifyContainer:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    identity: IdentityModule


def create_container(settings: Settings | None = None) -> HifyContainer:
    resolved_settings = settings or Settings()
    engine = create_engine(
        resolved_settings.database_url,
        echo=resolved_settings.database_echo,
    )
    session_factory = create_session_factory(engine)
    identity = create_identity_module(
        session_factory,
        allow_development_header_auth=resolved_settings.enable_development_header_auth,
    )
    return HifyContainer(
        settings=resolved_settings,
        engine=engine,
        session_factory=session_factory,
        identity=identity,
    )
