from __future__ import annotations

from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, ValidationError


class ConversationContractError(HifyError):
    code = "CONVERSATION_CONTRACT_ERROR"


class ConversationContractValidationError(ValidationError):
    code = "CONVERSATION_CONTRACT_VALIDATION_ERROR"


class ConversationContractNotFoundError(NotFoundError):
    code = "CONVERSATION_CONTRACT_NOT_FOUND"


class ConversationContractConflictError(ConflictError):
    code = "CONVERSATION_CONTRACT_CONFLICT"
