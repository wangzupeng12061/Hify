from __future__ import annotations

from hify.shared.domain.errors import (
    ConflictError,
    HifyError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)


class RunError(HifyError):
    code = "RUN_ERROR"


class RunValidationError(ValidationError):
    code = "RUN_VALIDATION_ERROR"


class RunNotFoundError(NotFoundError):
    code = "RUN_NOT_FOUND"


class RunPermissionDeniedError(PermissionDeniedError):
    code = "RUN_PERMISSION_DENIED"


class RunStateConflictError(ConflictError):
    code = "RUN_STATE_CONFLICT"
