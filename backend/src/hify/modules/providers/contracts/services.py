from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from hify.modules.providers.contracts.dto import (
    CallContext,
    EmbeddingRequest,
    EmbeddingResult,
    ModelChunk,
    ModelInfo,
    ModelPricingInfo,
    ModelRequest,
)


class ModelCatalog(Protocol):
    async def get_model(self, *, team_id: UUID, model_id: UUID) -> ModelInfo: ...

    async def list_models(self, *, team_id: UUID) -> tuple[ModelInfo, ...]: ...


class ModelPricingCatalog(Protocol):
    async def get_model_pricing(
        self,
        *,
        team_id: UUID,
        model_id: UUID,
    ) -> ModelPricingInfo | None: ...


class ModelGateway(Protocol):
    def stream(
        self,
        request: ModelRequest,
        context: CallContext,
    ) -> AsyncIterator[ModelChunk]: ...


class EmbeddingGateway(Protocol):
    async def embed(self, request: EmbeddingRequest, context: CallContext) -> EmbeddingResult: ...
