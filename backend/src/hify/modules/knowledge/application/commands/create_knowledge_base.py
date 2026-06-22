from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.knowledge.application.authorization import require_manage_knowledge
from hify.modules.knowledge.application.dto import knowledge_base_info_from_domain
from hify.modules.knowledge.application.ports import KnowledgeUnitOfWorkFactory
from hify.modules.knowledge.contracts.dto import KnowledgeBaseInfo
from hify.modules.knowledge.domain.entities import KnowledgeBase
from hify.modules.knowledge.domain.errors import (
    KnowledgeBaseAlreadyExistsError,
    KnowledgeValidationError,
)
from hify.modules.knowledge.domain.value_objects import (
    EMBEDDING_DIMENSIONS,
    normalize_knowledge_base_name,
)
from hify.modules.providers.contracts.services import ModelCatalog
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class CreateKnowledgeBaseCommand:
    actor: ActorContext
    name: str
    description: str | None
    embedding_model_id: UUID


class CreateKnowledgeBaseHandler:
    def __init__(
        self,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        model_catalog: ModelCatalog,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._model_catalog = model_catalog
        self._clock = clock

    async def handle(self, command: CreateKnowledgeBaseCommand) -> KnowledgeBaseInfo:
        require_manage_knowledge(command.actor)
        name = normalize_knowledge_base_name(command.name)
        model = await self._model_catalog.get_model(
            team_id=command.actor.team_id,
            model_id=command.embedding_model_id,
        )
        if model.kind != "embedding":
            raise KnowledgeValidationError("knowledge base requires an embedding model")

        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            existing = await unit_of_work.knowledge_bases.get_by_team_and_name(
                team_id=command.actor.team_id,
                name=name,
            )
            if existing is not None:
                raise KnowledgeBaseAlreadyExistsError("knowledge base already exists")
            knowledge_base = KnowledgeBase.create(
                team_id=command.actor.team_id,
                name=name,
                description=command.description,
                embedding_model_id=command.embedding_model_id,
                embedding_dimensions=EMBEDDING_DIMENSIONS,
                created_by=command.actor.user_id,
                now=now,
            )
            await unit_of_work.knowledge_bases.add(knowledge_base)
            await unit_of_work.commit()
        return knowledge_base_info_from_domain(knowledge_base)
