from __future__ import annotations

from hify.shared.domain.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError


class JobValidationError(ValidationError):
    code = "JOB_VALIDATION_ERROR"


class JobNotFoundError(NotFoundError):
    code = "JOB_NOT_FOUND"


class JobStateConflictError(ConflictError):
    code = "JOB_STATE_CONFLICT"


class JobPermissionDeniedError(PermissionDeniedError):
    code = "JOB_PERMISSION_DENIED"
