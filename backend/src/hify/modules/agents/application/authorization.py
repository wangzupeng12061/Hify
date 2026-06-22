from __future__ import annotations

from hify.modules.agents.domain.errors import AgentPermissionDeniedError
from hify.modules.identity.contracts.dto import ActorContext


MANAGE_AGENTS_PERMISSION = "agents.manage"


def require_manage_agents(actor: ActorContext) -> None:
    if not actor.has_permission(MANAGE_AGENTS_PERMISSION):
        raise AgentPermissionDeniedError("actor does not have permission to manage agents")
