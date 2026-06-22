from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from hify.modules.knowledge.domain.errors import KnowledgeBaseArchivedError
from hify.modules.knowledge.domain.value_objects import (
    DocumentStatus,
    KnowledgeBaseStatus,
    normalize_document_title,
    normalize_knowledge_base_description,
    normalize_knowledge_base_name,
    normalize_source_uri,
    validate_embedding_dimensions,
    validate_embedding_vector,
)
from hify.shared.domain.ids import new_uuid


@dataclass(slots=True)
class KnowledgeBase:
    id: UUID
    team_id: UUID
    name: str
    description: str | None
    status: KnowledgeBaseStatus
    embedding_model_id: UUID
    embedding_dimensions: int
    document_count: int
    chunk_count: int
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        name: str,
        description: str | None,
        embedding_model_id: UUID,
        embedding_dimensions: int,
        created_by: UUID,
        now: datetime,
    ) -> KnowledgeBase:
        validate_embedding_dimensions(embedding_dimensions)
        return cls(
            id=new_uuid(),
            team_id=team_id,
            name=normalize_knowledge_base_name(name),
            description=normalize_knowledge_base_description(description),
            status=KnowledgeBaseStatus.ACTIVE,
            embedding_model_id=embedding_model_id,
            embedding_dimensions=embedding_dimensions,
            document_count=0,
            chunk_count=0,
            version=0,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

    def ensure_active(self) -> None:
        if self.status is KnowledgeBaseStatus.ARCHIVED:
            raise KnowledgeBaseArchivedError("knowledge base is archived")

    def record_document_ingested(self, *, chunk_count: int, now: datetime) -> None:
        self.ensure_active()
        self.document_count += 1
        self.chunk_count += chunk_count
        self._mark_updated(now)

    def _mark_updated(self, now: datetime) -> None:
        self.version += 1
        self.updated_at = now


@dataclass(slots=True)
class KnowledgeDocument:
    id: UUID
    team_id: UUID
    knowledge_base_id: UUID
    title: str
    source_uri: str | None
    status: DocumentStatus
    chunk_count: int
    content_hash: str
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_completed(
        cls,
        *,
        team_id: UUID,
        knowledge_base_id: UUID,
        title: str,
        source_uri: str | None,
        chunk_count: int,
        content_hash: str,
        created_by: UUID,
        now: datetime,
    ) -> KnowledgeDocument:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            knowledge_base_id=knowledge_base_id,
            title=normalize_document_title(title),
            source_uri=normalize_source_uri(source_uri),
            status=DocumentStatus.COMPLETED,
            chunk_count=chunk_count,
            content_hash=content_hash,
            version=0,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )


@dataclass(slots=True)
class KnowledgeChunk:
    id: UUID
    team_id: UUID
    knowledge_base_id: UUID
    document_id: UUID
    position: int
    content: str
    embedding: tuple[float, ...]
    token_count: int
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        knowledge_base_id: UUID,
        document_id: UUID,
        position: int,
        content: str,
        embedding: tuple[float, ...],
        token_count: int,
        now: datetime,
    ) -> KnowledgeChunk:
        validate_embedding_vector(embedding)
        return cls(
            id=new_uuid(),
            team_id=team_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            position=position,
            content=content,
            embedding=embedding,
            token_count=token_count,
            created_at=now,
        )
