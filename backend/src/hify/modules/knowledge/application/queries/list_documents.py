from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.knowledge.application.authorization import require_manage_knowledge
from hify.modules.knowledge.application.dto import knowledge_document_info_from_domain
from hify.modules.knowledge.application.ports import KnowledgeUnitOfWorkFactory
from hify.modules.knowledge.contracts.dto import KnowledgeDocumentInfo
from hify.modules.knowledge.domain.errors import KnowledgeBaseNotFoundError


@dataclass(frozen=True, slots=True)
class ListKnowledgeDocumentsForActorQuery:
    actor: ActorContext
    knowledge_base_id: UUID


class ListKnowledgeDocumentsForActorHandler:
    def __init__(self, unit_of_work_factory: KnowledgeUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(
        self,
        query: ListKnowledgeDocumentsForActorQuery,
    ) -> tuple[KnowledgeDocumentInfo, ...]:
        require_manage_knowledge(query.actor)
        async with self._unit_of_work_factory() as unit_of_work:
            knowledge_base = await unit_of_work.knowledge_bases.get_by_id(query.knowledge_base_id)
            if knowledge_base is None or knowledge_base.team_id != query.actor.team_id:
                raise KnowledgeBaseNotFoundError("knowledge base was not found")
            documents = await unit_of_work.documents.list_by_knowledge_base(
                team_id=query.actor.team_id,
                knowledge_base_id=query.knowledge_base_id,
            )
        return tuple(knowledge_document_info_from_domain(item) for item in documents)
