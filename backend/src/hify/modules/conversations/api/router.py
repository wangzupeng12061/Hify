from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from hify.modules.conversations.api.dependencies import RequestAuthenticator
from hify.modules.conversations.api.schemas import (
    AppendConversationMessageRequest,
    ConversationMessagePageResponse,
    ConversationMessageResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageFeedbackResponse,
    SubmitMessageFeedbackRequest,
)
from hify.modules.conversations.application.commands.append_conversation_message import (
    AppendConversationMessageCommand,
    AppendConversationMessageHandler,
)
from hify.modules.conversations.application.commands.create_conversation import (
    CreateConversationCommand,
    CreateConversationHandler,
)
from hify.modules.conversations.application.commands.submit_message_feedback import (
    SubmitMessageFeedbackCommand,
    SubmitMessageFeedbackHandler,
)
from hify.modules.conversations.application.queries.list_conversation_messages import (
    ListConversationMessagesForActorHandler,
    ListConversationMessagesForActorQuery,
)
from hify.modules.identity.contracts.dto import ActorContext
from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, PermissionDeniedError


def create_conversations_router(
    *,
    create_conversation_handler: CreateConversationHandler,
    append_message_handler: AppendConversationMessageHandler,
    list_messages_handler: ListConversationMessagesForActorHandler,
    submit_feedback_handler: SubmitMessageFeedbackHandler,
    request_authenticator: RequestAuthenticator,
) -> APIRouter:
    router = APIRouter(prefix="/conversations", tags=["conversations"])

    async def get_current_actor(request: Request) -> ActorContext:
        try:
            return await request_authenticator.authenticate(request)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
    async def create_conversation(
        request: CreateConversationRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> ConversationResponse:
        try:
            command = CreateConversationCommand(
                actor=actor,
                agent_id=request.agent_id,
                title=request.title,
            )
            conversation = await create_conversation_handler.handle(command)
            return ConversationResponse.model_validate(conversation)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get(
        "/{conversation_id}/messages",
        response_model=ConversationMessagePageResponse,
    )
    async def list_conversation_messages(
        conversation_id: UUID,
        cursor: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
        actor: ActorContext = Depends(get_current_actor),
    ) -> ConversationMessagePageResponse:
        try:
            query = ListConversationMessagesForActorQuery(
                actor=actor,
                conversation_id=conversation_id,
                cursor=cursor,
                limit=limit,
            )
            page = await list_messages_handler.handle(query)
            return ConversationMessagePageResponse.model_validate(page)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post(
        "/{conversation_id}/messages",
        response_model=ConversationMessageResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def append_conversation_message(
        conversation_id: UUID,
        request: AppendConversationMessageRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> ConversationMessageResponse:
        try:
            command = AppendConversationMessageCommand(
                actor=actor,
                conversation_id=conversation_id,
                content=request.content,
                idempotency_key=request.idempotency_key,
            )
            message = await append_message_handler.handle(command)
            return ConversationMessageResponse.model_validate(message)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.put(
        "/{conversation_id}/messages/{message_id}/feedback",
        response_model=MessageFeedbackResponse,
    )
    async def submit_message_feedback(
        conversation_id: UUID,
        message_id: UUID,
        request: SubmitMessageFeedbackRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> MessageFeedbackResponse:
        try:
            command = SubmitMessageFeedbackCommand(
                actor=actor,
                conversation_id=conversation_id,
                message_id=message_id,
                rating=request.rating,
                comment=request.comment,
            )
            feedback = await submit_feedback_handler.handle(command)
            return MessageFeedbackResponse.model_validate(feedback)
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
