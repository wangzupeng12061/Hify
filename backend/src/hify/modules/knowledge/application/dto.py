from __future__ import annotations

from hify.modules.knowledge.contracts.dto import KnowledgeBaseInfo, KnowledgeDocumentInfo
from hify.modules.knowledge.domain.entities import KnowledgeBase, KnowledgeDocument


def knowledge_base_info_from_domain(knowledge_base: KnowledgeBase) -> KnowledgeBaseInfo:
    return KnowledgeBaseInfo(
        id=knowledge_base.id,
        team_id=knowledge_base.team_id,
        name=knowledge_base.name,
        description=knowledge_base.description,
        status=knowledge_base.status.value,
        embedding_model_id=knowledge_base.embedding_model_id,
        embedding_dimensions=knowledge_base.embedding_dimensions,
        document_count=knowledge_base.document_count,
        chunk_count=knowledge_base.chunk_count,
        created_at=knowledge_base.created_at,
        updated_at=knowledge_base.updated_at,
    )


def knowledge_document_info_from_domain(document: KnowledgeDocument) -> KnowledgeDocumentInfo:
    return KnowledgeDocumentInfo(
        id=document.id,
        team_id=document.team_id,
        knowledge_base_id=document.knowledge_base_id,
        title=document.title,
        source_uri=document.source_uri,
        status=document.status.value,
        chunk_count=document.chunk_count,
        content_hash=document.content_hash,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
