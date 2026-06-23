from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.knowledge.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.knowledge.api.router import create_knowledge_router
from hify.modules.knowledge.application.commands.create_knowledge_base import (
    CreateKnowledgeBaseHandler,
)
from hify.modules.knowledge.application.commands.ingest_document import IngestDocumentHandler
from hify.modules.knowledge.application.queries.get_knowledge_base import (
    GetKnowledgeBaseForActorHandler,
    KnowledgeBaseCatalogService,
    ListKnowledgeBasesForActorHandler,
)
from hify.modules.knowledge.application.queries.list_documents import (
    ListKnowledgeDocumentsForActorHandler,
)
from hify.modules.knowledge.application.queries.retrieve_chunks import KnowledgeRetrieverService
from hify.modules.knowledge.contracts.services import KnowledgeBaseCatalog, KnowledgeRetriever
from hify.modules.knowledge.infrastructure.database.uow import SqlAlchemyKnowledgeUnitOfWork
from hify.modules.providers.contracts.services import EmbeddingGateway, ModelCatalog
from hify.shared.domain.clock import Clock, SystemClock


@dataclass(frozen=True, slots=True)
class KnowledgeModule:
    router: APIRouter
    knowledge_base_catalog: KnowledgeBaseCatalog
    knowledge_retriever: KnowledgeRetriever


def create_knowledge_module(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    model_catalog: ModelCatalog,
    embedding_gateway: EmbeddingGateway,
    clock: Clock | None = None,
) -> KnowledgeModule:
    module_clock = clock or SystemClock()

    def unit_of_work_factory() -> SqlAlchemyKnowledgeUnitOfWork:
        return SqlAlchemyKnowledgeUnitOfWork(session_factory)

    create_knowledge_base_handler = CreateKnowledgeBaseHandler(
        unit_of_work_factory,
        model_catalog,
        module_clock,
    )
    list_knowledge_bases_handler = ListKnowledgeBasesForActorHandler(unit_of_work_factory)
    get_knowledge_base_handler = GetKnowledgeBaseForActorHandler(unit_of_work_factory)
    list_knowledge_documents_handler = ListKnowledgeDocumentsForActorHandler(unit_of_work_factory)
    ingest_document_handler = IngestDocumentHandler(
        unit_of_work_factory,
        embedding_gateway,
        module_clock,
    )
    knowledge_base_catalog = KnowledgeBaseCatalogService(unit_of_work_factory)
    knowledge_retriever = KnowledgeRetrieverService(unit_of_work_factory, embedding_gateway)
    router = create_knowledge_router(
        create_knowledge_base_handler=create_knowledge_base_handler,
        list_knowledge_bases_handler=list_knowledge_bases_handler,
        get_knowledge_base_handler=get_knowledge_base_handler,
        list_knowledge_documents_handler=list_knowledge_documents_handler,
        ingest_document_handler=ingest_document_handler,
        request_authenticator=AuthenticationNotConfiguredAuthenticator(),
    )
    return KnowledgeModule(
        router=router,
        knowledge_base_catalog=knowledge_base_catalog,
        knowledge_retriever=knowledge_retriever,
    )
