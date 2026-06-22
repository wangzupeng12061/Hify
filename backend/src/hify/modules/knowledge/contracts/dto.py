from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class KnowledgeBaseInfo:
    id: UUID
    team_id: UUID
    name: str
    description: str | None
    status: str
    embedding_model_id: UUID
    embedding_dimensions: int
    document_count: int
    chunk_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class KnowledgeDocumentInfo:
    id: UUID
    team_id: UUID
    knowledge_base_id: UUID
    title: str
    source_uri: str | None
    status: str
    chunk_count: int
    content_hash: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: UUID
    team_id: UUID
    knowledge_base_id: UUID
    document_id: UUID
    position: int
    content: str
    score: float
