from __future__ import annotations

from dataclasses import dataclass

from hify.modules.identity.application.ports import IdentityUnitOfWorkFactory
from hify.modules.identity.application.session_tokens import SessionTokenService
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class RevokeSessionCommand:
    token: str


class RevokeSessionHandler:
    def __init__(
        self,
        unit_of_work_factory: IdentityUnitOfWorkFactory,
        clock: Clock,
        session_tokens: SessionTokenService,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._session_tokens = session_tokens

    async def handle(self, command: RevokeSessionCommand) -> None:
        token_hash = self._session_tokens.hash_token(command.token)
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            session = await unit_of_work.sessions.get_by_token_hash(token_hash)
            if session is None:
                return

            session.revoke(now=now)
            await unit_of_work.sessions.save(session)
            await unit_of_work.commit()
