from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.knowledge.domain.entities import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from hify.modules.knowledge.domain.value_objects import DocumentStatus, KnowledgeBaseStatus
from hify.modules.knowledge.infrastructure.database.models import (
    KnowledgeBaseModel,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
)


class SqlAlchemyKnowledgeBaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, knowledge_base: KnowledgeBase) -> None:
        self._session.add(_knowledge_base_to_model(knowledge_base))

    async def save(self, knowledge_base: KnowledgeBase) -> None:
        model = await self._session.get(KnowledgeBaseModel, knowledge_base.id)
        if model is None:
            self._session.add(_knowledge_base_to_model(knowledge_base))
            return
        model.name = knowledge_base.name
        model.description = knowledge_base.description
        model.status = knowledge_base.status.value
        model.embedding_model_id = knowledge_base.embedding_model_id
        model.embedding_dimensions = knowledge_base.embedding_dimensions
        model.document_count = knowledge_base.document_count
        model.chunk_count = knowledge_base.chunk_count
        model.version = knowledge_base.version
        model.updated_at = knowledge_base.updated_at

    async def get_by_id(self, knowledge_base_id: UUID) -> KnowledgeBase | None:
        model = await self._session.get(KnowledgeBaseModel, knowledge_base_id)
        if model is None:
            return None
        return _knowledge_base_from_model(model)

    async def get_by_team_and_name(self, *, team_id: UUID, name: str) -> KnowledgeBase | None:
        statement = select(KnowledgeBaseModel).where(
            KnowledgeBaseModel.team_id == team_id,
            func.lower(KnowledgeBaseModel.name) == name.lower(),
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _knowledge_base_from_model(model)

    async def list_by_team(self, team_id: UUID) -> tuple[KnowledgeBase, ...]:
        statement = (
            select(KnowledgeBaseModel)
            .where(KnowledgeBaseModel.team_id == team_id)
            .order_by(KnowledgeBaseModel.created_at.desc(), KnowledgeBaseModel.id.desc())
        )
        models = await self._session.scalars(statement)
        return tuple(_knowledge_base_from_model(model) for model in models)


class SqlAlchemyKnowledgeDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: KnowledgeDocument) -> None:
        self._session.add(_document_to_model(document))

    async def list_by_knowledge_base(
        self,
        *,
        team_id: UUID,
        knowledge_base_id: UUID,
    ) -> tuple[KnowledgeDocument, ...]:
        statement = (
            select(KnowledgeDocumentModel)
            .where(
                KnowledgeDocumentModel.team_id == team_id,
                KnowledgeDocumentModel.knowledge_base_id == knowledge_base_id,
            )
            .order_by(KnowledgeDocumentModel.created_at.desc(), KnowledgeDocumentModel.id.desc())
        )
        models = await self._session.scalars(statement)
        return tuple(_document_from_model(model) for model in models)


class SqlAlchemyKnowledgeChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many(self, chunks: tuple[KnowledgeChunk, ...]) -> None:
        self._session.add_all(_chunk_to_model(chunk) for chunk in chunks)

    async def search_similar(
        self,
        *,
        team_id: UUID,
        knowledge_base_ids: tuple[UUID, ...],
        query_embedding: tuple[float, ...],
        limit: int,
    ) -> tuple[tuple[KnowledgeChunk, float], ...]:
        distance = KnowledgeChunkModel.embedding.cosine_distance(list(query_embedding)).label("distance")
        statement = (
            select(KnowledgeChunkModel, distance)
            .where(
                KnowledgeChunkModel.team_id == team_id,
                KnowledgeChunkModel.knowledge_base_id.in_(knowledge_base_ids),
            )
            .order_by(distance)
            .limit(limit)
        )
        rows = await self._session.execute(statement)
        return tuple((_chunk_from_model(model), float(score)) for model, score in rows.all())


def _knowledge_base_to_model(knowledge_base: KnowledgeBase) -> KnowledgeBaseModel:
    return KnowledgeBaseModel(
        id=knowledge_base.id,
        team_id=knowledge_base.team_id,
        name=knowledge_base.name,
        description=knowledge_base.description,
        status=knowledge_base.status.value,
        embedding_model_id=knowledge_base.embedding_model_id,
        embedding_dimensions=knowledge_base.embedding_dimensions,
        document_count=knowledge_base.document_count,
        chunk_count=knowledge_base.chunk_count,
        version=knowledge_base.version,
        created_by=knowledge_base.created_by,
        created_at=knowledge_base.created_at,
        updated_at=knowledge_base.updated_at,
    )


def _knowledge_base_from_model(model: KnowledgeBaseModel) -> KnowledgeBase:
    return KnowledgeBase(
        id=model.id,
        team_id=model.team_id,
        name=model.name,
        description=model.description,
        status=KnowledgeBaseStatus(model.status),
        embedding_model_id=model.embedding_model_id,
        embedding_dimensions=model.embedding_dimensions,
        document_count=model.document_count,
        chunk_count=model.chunk_count,
        version=model.version,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _document_to_model(document: KnowledgeDocument) -> KnowledgeDocumentModel:
    return KnowledgeDocumentModel(
        id=document.id,
        team_id=document.team_id,
        knowledge_base_id=document.knowledge_base_id,
        title=document.title,
        source_uri=document.source_uri,
        status=document.status.value,
        chunk_count=document.chunk_count,
        content_hash=document.content_hash,
        version=document.version,
        created_by=document.created_by,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _document_from_model(model: KnowledgeDocumentModel) -> KnowledgeDocument:
    return KnowledgeDocument(
        id=model.id,
        team_id=model.team_id,
        knowledge_base_id=model.knowledge_base_id,
        title=model.title,
        source_uri=model.source_uri,
        status=DocumentStatus(model.status),
        chunk_count=model.chunk_count,
        content_hash=model.content_hash,
        version=model.version,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _chunk_to_model(chunk: KnowledgeChunk) -> KnowledgeChunkModel:
    return KnowledgeChunkModel(
        id=chunk.id,
        team_id=chunk.team_id,
        knowledge_base_id=chunk.knowledge_base_id,
        document_id=chunk.document_id,
        position=chunk.position,
        content=chunk.content,
        embedding=list(chunk.embedding),
        token_count=chunk.token_count,
        created_at=chunk.created_at,
    )


def _chunk_from_model(model: KnowledgeChunkModel) -> KnowledgeChunk:
    return KnowledgeChunk(
        id=model.id,
        team_id=model.team_id,
        knowledge_base_id=model.knowledge_base_id,
        document_id=model.document_id,
        position=model.position,
        content=model.content,
        embedding=tuple(model.embedding),
        token_count=model.token_count,
        created_at=model.created_at,
    )
