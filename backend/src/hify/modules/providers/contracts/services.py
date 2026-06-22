from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.providers.contracts.dto import ModelInfo


class ModelCatalog(Protocol):
    async def get_model(self, *, team_id: UUID, model_id: UUID) -> ModelInfo: ...

    async def list_models(self, *, team_id: UUID) -> tuple[ModelInfo, ...]: ...
