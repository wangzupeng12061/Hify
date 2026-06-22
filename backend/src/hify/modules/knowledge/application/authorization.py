from __future__ import annotations

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.knowledge.domain.errors import KnowledgePermissionDeniedError


MANAGE_KNOWLEDGE_PERMISSION = "knowledge.manage"


def require_manage_knowledge(actor: ActorContext) -> None:
    if not actor.has_permission(MANAGE_KNOWLEDGE_PERMISSION):
        raise KnowledgePermissionDeniedError(
            "actor does not have permission to manage knowledge bases"
        )
