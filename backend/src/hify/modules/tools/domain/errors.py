from __future__ import annotations

from hify.shared.domain.errors import (
    ConflictError,
    HifyError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)


class ToolError(HifyError):
    code = "TOOL_ERROR"


class ToolValidationError(ValidationError):
    code = "TOOL_VALIDATION_ERROR"


class ToolNotFoundError(NotFoundError):
    code = "TOOL_NOT_FOUND"


class ToolAlreadyExistsError(ConflictError):
    code = "TOOL_ALREADY_EXISTS"


class ToolPermissionDeniedError(PermissionDeniedError):
    code = "TOOL_PERMISSION_DENIED"
