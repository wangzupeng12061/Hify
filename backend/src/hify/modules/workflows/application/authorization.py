from __future__ import annotations

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.workflows.domain.errors import WorkflowPermissionDeniedError


MANAGE_WORKFLOWS_PERMISSION = "workflows.manage"
READ_WORKFLOWS_PERMISSION = "workflows.read"


def require_manage_workflows(actor: ActorContext) -> None:
    if not actor.has_permission(MANAGE_WORKFLOWS_PERMISSION):
        raise WorkflowPermissionDeniedError("actor does not have permission to manage workflows")


def require_read_workflows(actor: ActorContext) -> None:
    if not actor.has_permission(READ_WORKFLOWS_PERMISSION):
        raise WorkflowPermissionDeniedError("actor does not have permission to read workflows")
