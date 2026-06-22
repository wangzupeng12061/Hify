from __future__ import annotations

from hify.shared.domain.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError


class KnowledgeValidationError(ValidationError):
    code = "KNOWLEDGE_VALIDATION_ERROR"


class KnowledgeBaseNotFoundError(NotFoundError):
    code = "KNOWLEDGE_BASE_NOT_FOUND"


class KnowledgeBaseAlreadyExistsError(ConflictError):
    code = "KNOWLEDGE_BASE_ALREADY_EXISTS"


class KnowledgeBaseArchivedError(ConflictError):
    code = "KNOWLEDGE_BASE_ARCHIVED"


class KnowledgePermissionDeniedError(PermissionDeniedError):
    code = "KNOWLEDGE_PERMISSION_DENIED"
