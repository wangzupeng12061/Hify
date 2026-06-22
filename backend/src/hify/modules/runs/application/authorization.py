from __future__ import annotations

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.runs.domain.errors import RunPermissionDeniedError


EXECUTE_RUNS_PERMISSION = "runs.execute"
READ_RUNS_PERMISSION = "runs.read"


def require_execute_runs(actor: ActorContext) -> None:
    if not actor.has_permission(EXECUTE_RUNS_PERMISSION):
        raise RunPermissionDeniedError("actor does not have permission to execute runs")


def require_read_runs(actor: ActorContext) -> None:
    if not actor.has_permission(READ_RUNS_PERMISSION):
        raise RunPermissionDeniedError("actor does not have permission to read runs")
