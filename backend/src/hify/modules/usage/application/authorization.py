from __future__ import annotations

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.usage.domain.errors import UsagePermissionDeniedError


READ_USAGE_PERMISSION = "usage.read"
MANAGE_USAGE_PERMISSION = "usage.manage"


def require_read_usage(actor: ActorContext) -> None:
    if not actor.has_permission(READ_USAGE_PERMISSION):
        raise UsagePermissionDeniedError("actor does not have permission to read usage")


def require_manage_usage(actor: ActorContext) -> None:
    if not actor.has_permission(MANAGE_USAGE_PERMISSION):
        raise UsagePermissionDeniedError("actor does not have permission to manage usage")
