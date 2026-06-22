from __future__ import annotations

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.tools.domain.errors import ToolPermissionDeniedError


MANAGE_TOOLS_PERMISSION = "tools.manage"
READ_TOOLS_PERMISSION = "tools.read"


def require_manage_tools(actor: ActorContext) -> None:
    if not actor.has_permission(MANAGE_TOOLS_PERMISSION):
        raise ToolPermissionDeniedError("actor does not have permission to manage tools")


def require_read_tools(actor: ActorContext) -> None:
    if not actor.has_permission(READ_TOOLS_PERMISSION):
        raise ToolPermissionDeniedError("actor does not have permission to read tools")
