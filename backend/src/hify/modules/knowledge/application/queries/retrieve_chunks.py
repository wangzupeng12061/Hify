from __future__ import annotations

from time import monotonic
from uuid import UUID

from hify.modules.knowledge.application.ports import KnowledgeUnitOfWorkFactory
from hify.modules.knowledge.contracts.dto import RetrievedChunk
from hify.modules.knowledge.contracts.services import KnowledgeRetriever
from hify.modules.knowledge.domain.errors import KnowledgeBaseNotFoundError, KnowledgeValidationError
from hify.modules.knowledge.domain.value_objects import normalize_document_content
from hify.modules.providers.contracts.dto import CallContext, EmbeddingRequest
from hify.modules.providers.contracts.services import EmbeddingGateway
from hify.shared.domain.ids import new_uuid


class KnowledgeRetrieverService(KnowledgeRetriever):
    def __init__(
        self,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        embedding_gateway: EmbeddingGateway,
        *,
        embedding_timeout_seconds: int = 60,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._embedding_gateway = embedding_gateway
        self._embedding_timeout_seconds = embedding_timeout_seconds

    async def retrieve(
        self,
        *,
        team_id: UUID,
        user_id: UUID,
        knowledge_base_ids: tuple[UUID, ...],
        query: str,
        limit: int,
    ) -> tuple[RetrievedChunk, ...]:
        if not knowledge_base_ids:
            return ()
        if limit < 1 or limit > 20:
            raise KnowledgeValidationError("retrieval limit must be between 1 and 20")
        normalized_query = normalize_document_content(query)

        async with self._unit_of_work_factory() as unit_of_work:
            knowledge_bases = []
            for knowledge_base_id in knowledge_base_ids:
                knowledge_base = await unit_of_work.knowledge_bases.get_by_id(knowledge_base_id)
                if knowledge_base is None or knowledge_base.team_id != team_id:
                    raise KnowledgeBaseNotFoundError("knowledge base was not found")
                knowledge_base.ensure_active()
                knowledge_bases.append(knowledge_base)

        embedding_result = await self._embedding_gateway.embed(
            EmbeddingRequest(
                model_id=knowledge_bases[0].embedding_model_id,
                input_texts=(normalized_query,),
            ),
            CallContext(
                run_id=new_uuid(),
                attempt_id=new_uuid(),
                team_id=team_id,
                user_id=user_id,
                deadline=monotonic() + self._embedding_timeout_seconds,
                cancellation=_NeverCancelledToken(),
            ),
        )
        if len(embedding_result.embeddings) != 1:
            raise KnowledgeValidationError("embedding result count does not match query count")

        async with self._unit_of_work_factory() as unit_of_work:
            matches = await unit_of_work.chunks.search_similar(
                team_id=team_id,
                knowledge_base_ids=knowledge_base_ids,
                query_embedding=embedding_result.embeddings[0],
                limit=limit,
            )
        return tuple(
            RetrievedChunk(
                chunk_id=chunk.id,
                team_id=chunk.team_id,
                knowledge_base_id=chunk.knowledge_base_id,
                document_id=chunk.document_id,
                position=chunk.position,
                content=chunk.content,
                score=1.0 - distance,
            )
            for chunk, distance in matches
        )


class _NeverCancelledToken:
    def is_cancelled(self) -> bool:
        return False

    def raise_if_cancelled(self) -> None:
        return None
