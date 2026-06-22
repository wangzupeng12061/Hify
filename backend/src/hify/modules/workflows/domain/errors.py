from __future__ import annotations

from hify.shared.domain.errors import (
    ConflictError,
    HifyError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)


class WorkflowError(HifyError):
    code = "WORKFLOW_ERROR"


class WorkflowValidationError(ValidationError):
    code = "WORKFLOW_VALIDATION_ERROR"


class WorkflowNotFoundError(NotFoundError):
    code = "WORKFLOW_NOT_FOUND"


class WorkflowAlreadyExistsError(ConflictError):
    code = "WORKFLOW_ALREADY_EXISTS"


class WorkflowVersionNotFoundError(NotFoundError):
    code = "WORKFLOW_VERSION_NOT_FOUND"


class WorkflowPermissionDeniedError(PermissionDeniedError):
    code = "WORKFLOW_PERMISSION_DENIED"
