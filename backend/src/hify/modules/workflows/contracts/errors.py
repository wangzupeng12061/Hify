from __future__ import annotations

from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, ValidationError


class WorkflowContractError(HifyError):
    code = "WORKFLOW_CONTRACT_ERROR"


class WorkflowContractValidationError(ValidationError):
    code = "WORKFLOW_CONTRACT_VALIDATION_ERROR"


class WorkflowContractNotFoundError(NotFoundError):
    code = "WORKFLOW_CONTRACT_NOT_FOUND"


class WorkflowContractConflictError(ConflictError):
    code = "WORKFLOW_CONTRACT_CONFLICT"
