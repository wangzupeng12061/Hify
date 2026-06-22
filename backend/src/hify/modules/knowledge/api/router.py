from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.knowledge.api.dependencies import RequestAuthenticator
from hify.modules.knowledge.api.schemas import (
    CreateKnowledgeBaseRequest,
    IngestDocumentRequest,
    KnowledgeBaseResponse,
    KnowledgeDocumentResponse,
)
from hify.modules.knowledge.application.commands.create_knowledge_base import (
    CreateKnowledgeBaseCommand,
    CreateKnowledgeBaseHandler,
)
from hify.modules.knowledge.application.commands.ingest_document import (
    IngestDocumentCommand,
    IngestDocumentHandler,
)
from hify.modules.knowledge.application.queries.get_knowledge_base import (
    GetKnowledgeBaseForActorHandler,
    GetKnowledgeBaseForActorQuery,
    ListKnowledgeBasesForActorHandler,
)
from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, PermissionDeniedError


def create_knowledge_router(
    *,
    create_knowledge_base_handler: CreateKnowledgeBaseHandler,
    list_knowledge_bases_handler: ListKnowledgeBasesForActorHandler,
    get_knowledge_base_handler: GetKnowledgeBaseForActorHandler,
    ingest_document_handler: IngestDocumentHandler,
    request_authenticator: RequestAuthenticator,
) -> APIRouter:
    router = APIRouter(prefix="/knowledge-bases", tags=["knowledge"])

    async def get_current_actor(request: Request) -> ActorContext:
        try:
            return await request_authenticator.authenticate(request)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
    async def create_knowledge_base(
        request: CreateKnowledgeBaseRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> KnowledgeBaseResponse:
        try:
            knowledge_base = await create_knowledge_base_handler.handle(
                CreateKnowledgeBaseCommand(
                    actor=actor,
                    name=request.name,
                    description=request.description,
                    embedding_model_id=request.embedding_model_id,
                )
            )
            return KnowledgeBaseResponse.model_validate(knowledge_base)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("", response_model=tuple[KnowledgeBaseResponse, ...])
    async def list_knowledge_bases(
        actor: ActorContext = Depends(get_current_actor),
    ) -> tuple[KnowledgeBaseResponse, ...]:
        try:
            knowledge_bases = await list_knowledge_bases_handler.handle(actor=actor)
            return tuple(KnowledgeBaseResponse.model_validate(item) for item in knowledge_bases)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/{knowledge_base_id}", response_model=KnowledgeBaseResponse)
    async def get_knowledge_base(
        knowledge_base_id: UUID,
        actor: ActorContext = Depends(get_current_actor),
    ) -> KnowledgeBaseResponse:
        try:
            knowledge_base = await get_knowledge_base_handler.handle(
                GetKnowledgeBaseForActorQuery(actor=actor, knowledge_base_id=knowledge_base_id)
            )
            return KnowledgeBaseResponse.model_validate(knowledge_base)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post(
        "/{knowledge_base_id}/documents",
        response_model=KnowledgeDocumentResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def ingest_document(
        knowledge_base_id: UUID,
        request: IngestDocumentRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> KnowledgeDocumentResponse:
        try:
            document = await ingest_document_handler.handle(
                IngestDocumentCommand(
                    actor=actor,
                    knowledge_base_id=knowledge_base_id,
                    title=request.title,
                    source_uri=request.source_uri,
                    content=request.content,
                )
            )
            return KnowledgeDocumentResponse.model_validate(document)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    return router


def _to_http_error(error: HifyError) -> HTTPException:
    if isinstance(error, PermissionDeniedError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(error, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, ConflictError):
        status_code = status.HTTP_409_CONFLICT
    else:
        status_code = status.HTTP_400_BAD_REQUEST

    detail = error.to_detail()
    return HTTPException(
        status_code=status_code,
        detail={
            "code": detail.code,
            "message": detail.message,
            "metadata": detail.metadata,
        },
    )
