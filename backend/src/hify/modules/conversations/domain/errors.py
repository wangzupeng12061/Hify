from __future__ import annotations

from hify.shared.domain.errors import (
    ConflictError,
    HifyError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)


class ConversationError(HifyError):
    code = "CONVERSATION_ERROR"


class ConversationValidationError(ValidationError):
    code = "CONVERSATION_VALIDATION_ERROR"


class ConversationNotFoundError(NotFoundError):
    code = "CONVERSATION_NOT_FOUND"


class ConversationMessageNotFoundError(NotFoundError):
    code = "CONVERSATION_MESSAGE_NOT_FOUND"


class ConversationPermissionDeniedError(PermissionDeniedError):
    code = "CONVERSATION_PERMISSION_DENIED"


class ConversationMessageConflictError(ConflictError):
    code = "CONVERSATION_MESSAGE_CONFLICT"
