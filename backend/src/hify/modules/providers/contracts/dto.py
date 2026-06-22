from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping, Protocol, TypeAlias
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


class CancellationToken(Protocol):
    def is_cancelled(self) -> bool: ...

    def raise_if_cancelled(self) -> None: ...


@dataclass(frozen=True, slots=True)
class CallContext:
    run_id: UUID
    attempt_id: UUID
    team_id: UUID
    user_id: UUID
    deadline: float
    cancellation: CancellationToken


@dataclass(frozen=True, slots=True)
class ModelMessage:
    role: Literal["system", "user", "assistant", "tool"]
    content: str


@dataclass(frozen=True, slots=True)
class ModelRequest:
    model_id: UUID
    messages: tuple[ModelMessage, ...]
    system_prompt: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    tools: tuple[Mapping[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class ModelUsage:
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class TextDeltaChunk:
    chunk_type: Literal["text_delta"]
    text: str


@dataclass(frozen=True, slots=True)
class ReasoningDeltaChunk:
    chunk_type: Literal["reasoning_delta"]
    text: str


@dataclass(frozen=True, slots=True)
class ToolCallDeltaChunk:
    chunk_type: Literal["tool_call_delta"]
    tool_call_id: str
    name: str
    arguments_delta: str


@dataclass(frozen=True, slots=True)
class UsageChunk:
    chunk_type: Literal["usage"]
    usage: ModelUsage


@dataclass(frozen=True, slots=True)
class DoneChunk:
    chunk_type: Literal["done"]
    finish_reason: Literal["stop", "length", "tool_calls", "content_filter", "cancelled"]


@dataclass(frozen=True, slots=True)
class ErrorChunk:
    chunk_type: Literal["error"]
    error_code: str
    message: str


ModelChunk: TypeAlias = (
    TextDeltaChunk
    | ReasoningDeltaChunk
    | ToolCallDeltaChunk
    | UsageChunk
    | DoneChunk
    | ErrorChunk
)
