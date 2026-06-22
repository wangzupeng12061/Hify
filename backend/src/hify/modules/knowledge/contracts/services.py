from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.knowledge.contracts.dto import KnowledgeBaseInfo, RetrievedChunk


class KnowledgeBaseCatalog(Protocol):
    async def get_knowledge_base(
        self,
        *,
        team_id: UUID,
        knowledge_base_id: UUID,
    ) -> KnowledgeBaseInfo: ...


class KnowledgeRetriever(Protocol):
    async def retrieve(
        self,
        *,
        team_id: UUID,
        user_id: UUID,
        knowledge_base_ids: tuple[UUID, ...],
        query: str,
        limit: int,
        deadline: float | None = None,
    ) -> tuple[RetrievedChunk, ...]: ...
