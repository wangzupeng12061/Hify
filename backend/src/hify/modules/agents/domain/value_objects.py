from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from hify.modules.agents.domain.errors import AgentValidationError


class AgentStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


def normalize_agent_name(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise AgentValidationError("agent name must not be blank")
    if len(normalized) > 120:
        raise AgentValidationError("agent name must be at most 120 characters")
    return normalized


def normalize_agent_description(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    if len(normalized) > 500:
        raise AgentValidationError("agent description must be at most 500 characters")
    return normalized


def normalize_system_prompt(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise AgentValidationError("system prompt must not be blank")
    if len(normalized) > 20000:
        raise AgentValidationError("system prompt must be at most 20000 characters")
    return normalized


@dataclass(frozen=True, slots=True)
class ModelBindingSnapshot:
    provider_model_id: UUID
    provider_type: str
    provider_name: str
    model_name: str
    model_display_name: str
    context_window_tokens: int
    supports_tools: bool
    supports_vision: bool
    supports_structured_output: bool

    def __post_init__(self) -> None:
        if self.context_window_tokens < 1:
            raise AgentValidationError("model context window tokens must be positive")
