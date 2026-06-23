from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.knowledge.application.commands.create_knowledge_base import (
    CreateKnowledgeBaseCommand,
    CreateKnowledgeBaseHandler,
)
from hify.modules.knowledge.application.commands.ingest_document import (
    IngestDocumentCommand,
    IngestDocumentHandler,
)
from hify.modules.knowledge.application.queries.retrieve_chunks import KnowledgeRetrieverService
from hify.modules.knowledge.domain.entities import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from hify.modules.knowledge.domain.errors import (
    KnowledgeBaseAlreadyExistsError,
    KnowledgePermissionDeniedError,
    KnowledgeValidationError,
)
from hify.modules.knowledge.domain.value_objects import EMBEDDING_DIMENSIONS
from hify.modules.providers.contracts.dto import (
    CallContext,
    EmbeddingRequest,
    EmbeddingResult,
    ModelInfo,
)
from hify.shared.domain.clock import Clock


class FixedClock(Clock):
    def now(self) -> datetime:
        return datetime(2026, 6, 22, tzinfo=UTC)


class FakeKnowledgeBaseRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, KnowledgeBase] = {}

    async def add(self, knowledge_base: KnowledgeBase) -> None:
        self.items[knowledge_base.id] = knowledge_base

    async def save(self, knowledge_base: KnowledgeBase) -> None:
        self.items[knowledge_base.id] = knowledge_base

    async def get_by_id(self, knowledge_base_id: UUID) -> KnowledgeBase | None:
        return self.items.get(knowledge_base_id)

    async def get_by_team_and_name(self, *, team_id: UUID, name: str) -> KnowledgeBase | None:
        for knowledge_base in self.items.values():
            if knowledge_base.team_id == team_id and knowledge_base.name.lower() == name.lower():
                return knowledge_base
        return None

    async def list_by_team(self, team_id: UUID) -> tuple[KnowledgeBase, ...]:
        items = [item for item in self.items.values() if item.team_id == team_id]
        return tuple(sorted(items, key=lambda item: (item.created_at, item.id), reverse=True))


class FakeKnowledgeDocumentRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, KnowledgeDocument] = {}

    async def add(self, document: KnowledgeDocument) -> None:
        self.items[document.id] = document

    async def list_by_knowledge_base(
        self,
        *,
        team_id: UUID,
        knowledge_base_id: UUID,
    ) -> tuple[KnowledgeDocument, ...]:
        items = [
            item
            for item in self.items.values()
            if item.team_id == team_id and item.knowledge_base_id == knowledge_base_id
        ]
        return tuple(sorted(items, key=lambda item: (item.created_at, item.id), reverse=True))


class FakeKnowledgeChunkRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, KnowledgeChunk] = {}

    async def add_many(self, chunks: tuple[KnowledgeChunk, ...]) -> None:
        for chunk in chunks:
            self.items[chunk.id] = chunk

    async def search_similar(
        self,
        *,
        team_id: UUID,
        knowledge_base_ids: tuple[UUID, ...],
        query_embedding: tuple[float, ...],
        limit: int,
    ) -> tuple[tuple[KnowledgeChunk, float], ...]:
        _ = query_embedding
        matches = [
            (chunk, 0.2)
            for chunk in self.items.values()
            if chunk.team_id == team_id and chunk.knowledge_base_id in knowledge_base_ids
        ]
        return tuple(matches[:limit])


class FakeKnowledgeUnitOfWork:
    def __init__(self) -> None:
        self.knowledge_bases = FakeKnowledgeBaseRepository()
        self.documents = FakeKnowledgeDocumentRepository()
        self.chunks = FakeKnowledgeChunkRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeModelCatalog:
    def __init__(self, *, kind: str = "embedding") -> None:
        self.kind = kind

    async def get_model(self, *, team_id: UUID, model_id: UUID) -> ModelInfo:
        return ModelInfo(
            id=model_id,
            team_id=team_id,
            provider_id=UUID("00000000-0000-7000-8000-000000000004"),
            provider_type="openai",
            provider_name="OpenAI",
            model_name="text-embedding-3-small",
            display_name="Embedding",
            kind=self.kind,
            status="active",
            context_window_tokens=8192,
            supports_tools=False,
            supports_vision=False,
            supports_structured_output=False,
            price_per_1m_input_tokens=None,
            price_per_1m_output_tokens=None,
        )

    async def list_models(self, *, team_id: UUID) -> tuple[ModelInfo, ...]:
        _ = team_id
        return ()


class RecordingEmbeddingGateway:
    def __init__(self) -> None:
        self.requests: list[EmbeddingRequest] = []
        self.contexts: list[CallContext] = []

    async def embed(self, request: EmbeddingRequest, context: CallContext) -> EmbeddingResult:
        self.requests.append(request)
        self.contexts.append(context)
        embedding = tuple(0.001 for _ in range(EMBEDDING_DIMENSIONS))
        return EmbeddingResult(embeddings=tuple(embedding for _ in request.input_texts))


def actor_with_knowledge_permission() -> ActorContext:
    return ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="admin",
        permissions=("knowledge.manage",),
    )


@pytest.mark.asyncio
async def test_create_knowledge_base_requires_embedding_model() -> None:
    unit_of_work = FakeKnowledgeUnitOfWork()
    actor = actor_with_knowledge_permission()
    handler = CreateKnowledgeBaseHandler(lambda: unit_of_work, FakeModelCatalog(), FixedClock())
    model_id = UUID("00000000-0000-7000-8000-000000000010")

    knowledge_base = await handler.handle(
        CreateKnowledgeBaseCommand(
            actor=actor,
            name="Team Docs",
            description="Internal docs",
            embedding_model_id=model_id,
        )
    )

    assert knowledge_base.name == "Team Docs"
    assert knowledge_base.embedding_model_id == model_id
    assert knowledge_base.embedding_dimensions == EMBEDDING_DIMENSIONS
    assert unit_of_work.committed


@pytest.mark.asyncio
async def test_create_knowledge_base_rejects_duplicate_name() -> None:
    unit_of_work = FakeKnowledgeUnitOfWork()
    actor = actor_with_knowledge_permission()
    handler = CreateKnowledgeBaseHandler(lambda: unit_of_work, FakeModelCatalog(), FixedClock())
    command = CreateKnowledgeBaseCommand(
        actor=actor,
        name="Team Docs",
        description=None,
        embedding_model_id=UUID("00000000-0000-7000-8000-000000000010"),
    )

    await handler.handle(command)
    with pytest.raises(KnowledgeBaseAlreadyExistsError):
        await handler.handle(command)


@pytest.mark.asyncio
async def test_create_knowledge_base_requires_manage_permission() -> None:
    actor = ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="viewer",
        permissions=(),
    )
    handler = CreateKnowledgeBaseHandler(
        lambda: FakeKnowledgeUnitOfWork(),
        FakeModelCatalog(),
        FixedClock(),
    )

    with pytest.raises(KnowledgePermissionDeniedError):
        await handler.handle(
            CreateKnowledgeBaseCommand(
                actor=actor,
                name="Team Docs",
                description=None,
                embedding_model_id=UUID("00000000-0000-7000-8000-000000000010"),
            )
        )


@pytest.mark.asyncio
async def test_create_knowledge_base_rejects_chat_model() -> None:
    actor = actor_with_knowledge_permission()
    handler = CreateKnowledgeBaseHandler(
        lambda: FakeKnowledgeUnitOfWork(),
        FakeModelCatalog(kind="chat"),
        FixedClock(),
    )

    with pytest.raises(KnowledgeValidationError):
        await handler.handle(
            CreateKnowledgeBaseCommand(
                actor=actor,
                name="Team Docs",
                description=None,
                embedding_model_id=UUID("00000000-0000-7000-8000-000000000010"),
            )
        )


@pytest.mark.asyncio
async def test_ingest_document_splits_embeds_and_persists_chunks() -> None:
    unit_of_work = FakeKnowledgeUnitOfWork()
    actor = actor_with_knowledge_permission()
    knowledge_base = await CreateKnowledgeBaseHandler(
        lambda: unit_of_work,
        FakeModelCatalog(),
        FixedClock(),
    ).handle(
        CreateKnowledgeBaseCommand(
            actor=actor,
            name="Team Docs",
            description=None,
            embedding_model_id=UUID("00000000-0000-7000-8000-000000000010"),
        )
    )
    embedding_gateway = RecordingEmbeddingGateway()
    handler = IngestDocumentHandler(lambda: unit_of_work, embedding_gateway, FixedClock())

    document = await handler.handle(
        IngestDocumentCommand(
            actor=actor,
            knowledge_base_id=knowledge_base.id,
            title="Runbook",
            source_uri="s3://bucket/runbook.md",
            content="A" * 1400,
        )
    )

    assert document.title == "Runbook"
    assert document.chunk_count == 2
    assert len(embedding_gateway.requests[0].input_texts) == 2
    assert len(unit_of_work.chunks.items) == 2
    updated_knowledge_base = unit_of_work.knowledge_bases.items[knowledge_base.id]
    assert updated_knowledge_base.document_count == 1
    assert updated_knowledge_base.chunk_count == 2


@pytest.mark.asyncio
async def test_retriever_embeds_query_and_returns_ranked_chunks() -> None:
    unit_of_work = FakeKnowledgeUnitOfWork()
    actor = actor_with_knowledge_permission()
    knowledge_base = await CreateKnowledgeBaseHandler(
        lambda: unit_of_work,
        FakeModelCatalog(),
        FixedClock(),
    ).handle(
        CreateKnowledgeBaseCommand(
            actor=actor,
            name="Team Docs",
            description=None,
            embedding_model_id=UUID("00000000-0000-7000-8000-000000000010"),
        )
    )
    embedding_gateway = RecordingEmbeddingGateway()
    await IngestDocumentHandler(lambda: unit_of_work, embedding_gateway, FixedClock()).handle(
        IngestDocumentCommand(
            actor=actor,
            knowledge_base_id=knowledge_base.id,
            title="Runbook",
            source_uri=None,
            content="How to restart the API",
        )
    )
    retriever = KnowledgeRetrieverService(lambda: unit_of_work, embedding_gateway)

    chunks = await retriever.retrieve(
        team_id=actor.team_id,
        user_id=actor.user_id,
        knowledge_base_ids=(knowledge_base.id,),
        query="restart api",
        limit=3,
        deadline=123.0,
    )

    assert len(chunks) == 1
    assert chunks[0].content == "How to restart the API"
    assert chunks[0].score == pytest.approx(0.8)
