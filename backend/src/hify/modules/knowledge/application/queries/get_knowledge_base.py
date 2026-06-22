from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.knowledge.application.authorization import require_manage_knowledge
from hify.modules.knowledge.application.dto import knowledge_base_info_from_domain
from hify.modules.knowledge.application.ports import KnowledgeUnitOfWorkFactory
from hify.modules.knowledge.contracts.dto import KnowledgeBaseInfo
from hify.modules.knowledge.domain.errors import KnowledgeBaseNotFoundError


@dataclass(frozen=True, slots=True)
class GetKnowledgeBaseForActorQuery:
    actor: ActorContext
    knowledge_base_id: UUID


class GetKnowledgeBaseForActorHandler:
    def __init__(self, unit_of_work_factory: KnowledgeUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetKnowledgeBaseForActorQuery) -> KnowledgeBaseInfo:
        require_manage_knowledge(query.actor)
        async with self._unit_of_work_factory() as unit_of_work:
            knowledge_base = await unit_of_work.knowledge_bases.get_by_id(query.knowledge_base_id)
        if knowledge_base is None or knowledge_base.team_id != query.actor.team_id:
            raise KnowledgeBaseNotFoundError("knowledge base was not found")
        return knowledge_base_info_from_domain(knowledge_base)


class ListKnowledgeBasesForActorHandler:
    def __init__(self, unit_of_work_factory: KnowledgeUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, *, actor: ActorContext) -> tuple[KnowledgeBaseInfo, ...]:
        require_manage_knowledge(actor)
        async with self._unit_of_work_factory() as unit_of_work:
            knowledge_bases = await unit_of_work.knowledge_bases.list_by_team(actor.team_id)
        return tuple(knowledge_base_info_from_domain(item) for item in knowledge_bases)
