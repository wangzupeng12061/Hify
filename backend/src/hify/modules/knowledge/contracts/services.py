from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.knowledge.contracts.dto import RetrievedChunk


class KnowledgeRetriever(Protocol):
    async def retrieve(
        self,
        *,
        team_id: UUID,
        user_id: UUID,
        knowledge_base_ids: tuple[UUID, ...],
        query: str,
        limit: int,
    ) -> tuple[RetrievedChunk, ...]: ...
