from __future__ import annotations

from hify.modules.conversations.domain.errors import ConversationPermissionDeniedError
from hify.modules.identity.contracts.dto import ActorContext


EXECUTE_RUNS_PERMISSION = "runs.execute"
READ_RUNS_PERMISSION = "runs.read"


def require_execute_conversations(actor: ActorContext) -> None:
    if not actor.has_permission(EXECUTE_RUNS_PERMISSION):
        raise ConversationPermissionDeniedError(
            "actor does not have permission to create conversation messages"
        )


def require_read_conversations(actor: ActorContext) -> None:
    if not actor.has_permission(READ_RUNS_PERMISSION):
        raise ConversationPermissionDeniedError("actor does not have permission to read conversations")
