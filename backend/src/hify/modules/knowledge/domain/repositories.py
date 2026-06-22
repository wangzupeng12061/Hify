from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.knowledge.domain.entities import KnowledgeBase, KnowledgeChunk, KnowledgeDocument


class KnowledgeBaseRepository(Protocol):
    async def add(self, knowledge_base: KnowledgeBase) -> None: ...

    async def save(self, knowledge_base: KnowledgeBase) -> None: ...

    async def get_by_id(self, knowledge_base_id: UUID) -> KnowledgeBase | None: ...

    async def get_by_team_and_name(self, *, team_id: UUID, name: str) -> KnowledgeBase | None: ...

    async def list_by_team(self, team_id: UUID) -> tuple[KnowledgeBase, ...]: ...


class KnowledgeDocumentRepository(Protocol):
    async def add(self, document: KnowledgeDocument) -> None: ...

    async def list_by_knowledge_base(
        self,
        *,
        team_id: UUID,
        knowledge_base_id: UUID,
    ) -> tuple[KnowledgeDocument, ...]: ...


class KnowledgeChunkRepository(Protocol):
    async def add_many(self, chunks: tuple[KnowledgeChunk, ...]) -> None: ...

    async def search_similar(
        self,
        *,
        team_id: UUID,
        knowledge_base_ids: tuple[UUID, ...],
        query_embedding: tuple[float, ...],
        limit: int,
    ) -> tuple[tuple[KnowledgeChunk, float], ...]: ...
