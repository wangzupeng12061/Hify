from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateKnowledgeBaseRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    embedding_model_id: UUID


class IngestDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source_uri: str | None = Field(default=None, max_length=1000)
    content: str = Field(min_length=1, max_length=200_000)


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
