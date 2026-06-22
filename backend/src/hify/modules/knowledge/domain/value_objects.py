from __future__ import annotations

from enum import StrEnum

from hify.modules.knowledge.domain.errors import KnowledgeValidationError


EMBEDDING_DIMENSIONS = 1536
MAX_DOCUMENT_CHARACTERS = 200_000
MAX_CHUNK_CHARACTERS = 1_200
CHUNK_OVERLAP_CHARACTERS = 200


class KnowledgeBaseStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class DocumentStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


def normalize_knowledge_base_name(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise KnowledgeValidationError("knowledge base name must not be blank")
    if len(normalized) > 120:
        raise KnowledgeValidationError("knowledge base name must be at most 120 characters")
    return normalized


def normalize_knowledge_base_description(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    if len(normalized) > 500:
        raise KnowledgeValidationError("knowledge base description must be at most 500 characters")
    return normalized


def normalize_document_title(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise KnowledgeValidationError("document title must not be blank")
    if len(normalized) > 200:
        raise KnowledgeValidationError("document title must be at most 200 characters")
    return normalized


def normalize_source_uri(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > 1000:
        raise KnowledgeValidationError("document source uri must be at most 1000 characters")
    return normalized


def normalize_document_content(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise KnowledgeValidationError("document content must not be blank")
    if len(normalized) > MAX_DOCUMENT_CHARACTERS:
        raise KnowledgeValidationError("document content exceeds maximum length")
    return normalized


def validate_embedding_dimensions(value: int) -> None:
    if value != EMBEDDING_DIMENSIONS:
        raise KnowledgeValidationError(
            f"embedding dimensions must be {EMBEDDING_DIMENSIONS} for the initial RAG store"
        )


def validate_embedding_vector(value: tuple[float, ...]) -> None:
    if len(value) != EMBEDDING_DIMENSIONS:
        raise KnowledgeValidationError("embedding vector dimensions do not match the knowledge base")
