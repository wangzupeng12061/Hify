from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import monotonic
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.knowledge.application.authorization import require_manage_knowledge
from hify.modules.knowledge.application.dto import knowledge_document_info_from_domain
from hify.modules.knowledge.application.ports import KnowledgeUnitOfWorkFactory
from hify.modules.knowledge.contracts.dto import KnowledgeDocumentInfo
from hify.modules.knowledge.domain.entities import KnowledgeChunk, KnowledgeDocument
from hify.modules.knowledge.domain.errors import KnowledgeBaseNotFoundError, KnowledgeValidationError
from hify.modules.knowledge.domain.services import split_document_text
from hify.modules.knowledge.domain.value_objects import normalize_document_content
from hify.modules.providers.contracts.dto import CallContext, EmbeddingRequest
from hify.modules.providers.contracts.services import EmbeddingGateway
from hify.shared.domain.clock import Clock
from hify.shared.domain.ids import new_uuid


@dataclass(frozen=True, slots=True)
class IngestDocumentCommand:
    actor: ActorContext
    knowledge_base_id: UUID
    title: str
    source_uri: str | None
    content: str


class IngestDocumentHandler:
    def __init__(
        self,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        embedding_gateway: EmbeddingGateway,
        clock: Clock,
        *,
        embedding_timeout_seconds: int = 120,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._embedding_gateway = embedding_gateway
        self._clock = clock
        self._embedding_timeout_seconds = embedding_timeout_seconds

    async def handle(self, command: IngestDocumentCommand) -> KnowledgeDocumentInfo:
        require_manage_knowledge(command.actor)
        content = normalize_document_content(command.content)
        chunks = split_document_text(content)

        async with self._unit_of_work_factory() as unit_of_work:
            knowledge_base = await unit_of_work.knowledge_bases.get_by_id(command.knowledge_base_id)
        if knowledge_base is None or knowledge_base.team_id != command.actor.team_id:
            raise KnowledgeBaseNotFoundError("knowledge base was not found")
        knowledge_base.ensure_active()

        embedding_result = await self._embedding_gateway.embed(
            EmbeddingRequest(
                model_id=knowledge_base.embedding_model_id,
                input_texts=chunks,
            ),
            CallContext(
                run_id=new_uuid(),
                attempt_id=new_uuid(),
                team_id=command.actor.team_id,
                user_id=command.actor.user_id,
                deadline=monotonic() + self._embedding_timeout_seconds,
                cancellation=_NeverCancelledToken(),
            ),
        )
        if len(embedding_result.embeddings) != len(chunks):
            raise KnowledgeValidationError("embedding result count does not match chunk count")

        now = self._clock.now()
        document = KnowledgeDocument.create_completed(
            team_id=command.actor.team_id,
            knowledge_base_id=knowledge_base.id,
            title=command.title,
            source_uri=command.source_uri,
            chunk_count=len(chunks),
            content_hash=sha256(content.encode("utf-8")).hexdigest(),
            created_by=command.actor.user_id,
            now=now,
        )
        chunk_entities = tuple(
            KnowledgeChunk.create(
                team_id=command.actor.team_id,
                knowledge_base_id=knowledge_base.id,
                document_id=document.id,
                position=index,
                content=chunk,
                embedding=embedding_result.embeddings[index],
                token_count=max(1, len(chunk) // 4),
                now=now,
            )
            for index, chunk in enumerate(chunks)
        )

        async with self._unit_of_work_factory() as unit_of_work:
            current_knowledge_base = await unit_of_work.knowledge_bases.get_by_id(knowledge_base.id)
            if current_knowledge_base is None or current_knowledge_base.team_id != command.actor.team_id:
                raise KnowledgeBaseNotFoundError("knowledge base was not found")
            current_knowledge_base.record_document_ingested(chunk_count=len(chunk_entities), now=now)
            await unit_of_work.documents.add(document)
            await unit_of_work.chunks.add_many(chunk_entities)
            await unit_of_work.knowledge_bases.save(current_knowledge_base)
            await unit_of_work.commit()

        return knowledge_document_info_from_domain(document)


class _NeverCancelledToken:
    def is_cancelled(self) -> bool:
        return False

    def raise_if_cancelled(self) -> None:
        return None
