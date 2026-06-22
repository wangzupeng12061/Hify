from __future__ import annotations

from types import TracebackType
from typing import Protocol

from hify.modules.knowledge.domain.repositories import (
    KnowledgeBaseRepository,
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
)


class KnowledgeUnitOfWork(Protocol):
    knowledge_bases: KnowledgeBaseRepository
    documents: KnowledgeDocumentRepository
    chunks: KnowledgeChunkRepository

    async def __aenter__(self) -> KnowledgeUnitOfWork: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class KnowledgeUnitOfWorkFactory(Protocol):
    def __call__(self) -> KnowledgeUnitOfWork: ...
