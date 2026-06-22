from __future__ import annotations

from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, ValidationError


class AgentContractError(HifyError):
    code = "AGENT_CONTRACT_ERROR"


class AgentContractValidationError(ValidationError):
    code = "AGENT_CONTRACT_VALIDATION_ERROR"


class AgentContractNotFoundError(NotFoundError):
    code = "AGENT_CONTRACT_NOT_FOUND"


class AgentContractConflictError(ConflictError):
    code = "AGENT_CONTRACT_CONFLICT"
