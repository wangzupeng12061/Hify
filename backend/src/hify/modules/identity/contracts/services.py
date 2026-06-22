from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext


class IdentityAccess(Protocol):
    async def get_actor_context(self, *, user_id: UUID, team_id: UUID) -> ActorContext: ...

    async def require_permission(self, actor: ActorContext, permission: str) -> None: ...
