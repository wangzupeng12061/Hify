from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    id: UUID
    team_id: UUID
    provider_type: str
    name: str
    base_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ModelInfo:
    id: UUID
    team_id: UUID
    provider_id: UUID
    provider_type: str
    provider_name: str
    model_name: str
    display_name: str
    kind: str
    status: str
    context_window_tokens: int
    supports_tools: bool
    supports_vision: bool
    supports_structured_output: bool


@dataclass(frozen=True, slots=True)
class CredentialWriteResult:
    fingerprint: str
    key_version: int
