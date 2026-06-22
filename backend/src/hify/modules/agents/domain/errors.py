from __future__ import annotations

from hify.shared.domain.errors import (
    ConflictError,
    HifyError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)


class AgentError(HifyError):
    code = "AGENT_ERROR"


class AgentValidationError(ValidationError):
    code = "AGENT_VALIDATION_ERROR"


class AgentNotFoundError(NotFoundError):
    code = "AGENT_NOT_FOUND"


class AgentAlreadyExistsError(ConflictError):
    code = "AGENT_ALREADY_EXISTS"


class AgentVersionNotFoundError(NotFoundError):
    code = "AGENT_VERSION_NOT_FOUND"


class AgentPermissionDeniedError(PermissionDeniedError):
    code = "AGENT_PERMISSION_DENIED"
