from __future__ import annotations

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.jobs.domain.errors import JobPermissionDeniedError


READ_JOBS_PERMISSION = "jobs.read"


def require_read_jobs(actor: ActorContext) -> None:
    if not actor.has_permission(READ_JOBS_PERMISSION):
        raise JobPermissionDeniedError("actor does not have permission to read jobs")
