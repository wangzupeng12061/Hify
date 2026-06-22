from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from time import monotonic

from hify.modules.providers.contracts.dto import (
    CallContext,
    EmbeddingRequest,
    EmbeddingResult,
    ModelChunk,
    ModelRequest,
)
from hify.modules.providers.contracts.errors import (
    ProviderCancelledError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from hify.modules.providers.contracts.services import EmbeddingGateway, ModelGateway


class MissingModelGateway(ModelGateway):
    def stream(
        self,
        request: ModelRequest,
        context: CallContext,
    ) -> AsyncIterator[ModelChunk]:
        return self._stream(request, context)

    async def _stream(
        self,
        request: ModelRequest,
        context: CallContext,
    ) -> AsyncIterator[ModelChunk]:
        _ = request
        _ = context
        raise ProviderUnavailableError("model gateway is not configured")
        if False:
            yield


class MissingEmbeddingGateway(EmbeddingGateway):
    async def embed(self, request: EmbeddingRequest, context: CallContext) -> EmbeddingResult:
        _ = request
        _ = context
        raise ProviderUnavailableError("embedding gateway is not configured")


class StaticModelGateway(ModelGateway):
    def __init__(self, chunks: Sequence[ModelChunk]) -> None:
        self._chunks = tuple(chunks)

    def stream(
        self,
        request: ModelRequest,
        context: CallContext,
    ) -> AsyncIterator[ModelChunk]:
        return self._stream(request, context)

    async def _stream(
        self,
        request: ModelRequest,
        context: CallContext,
    ) -> AsyncIterator[ModelChunk]:
        _ = request
        for chunk in self._chunks:
            context.cancellation.raise_if_cancelled()
            if context.cancellation.is_cancelled():
                raise ProviderCancelledError("model call was cancelled")
            if monotonic() >= context.deadline:
                raise ProviderTimeoutError("model call deadline exceeded", timeout_stage="deadline")
            yield chunk
