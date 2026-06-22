from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from enum import StrEnum
from uuid import UUID

from hify.modules.agents.domain.errors import AgentValidationError


class AgentStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


MAX_AGENT_KNOWLEDGE_BASES = 10


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


def normalize_knowledge_base_ids(values: tuple[UUID, ...]) -> tuple[UUID, ...]:
    seen: set[UUID] = set()
    normalized: list[UUID] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    if len(normalized) > MAX_AGENT_KNOWLEDGE_BASES:
        raise AgentValidationError("agent can bind at most 10 knowledge bases")
    return tuple(normalized)


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


@dataclass(frozen=True, slots=True)
class WorkflowBindingSnapshot:
    workflow_id: UUID
    workflow_version_id: UUID
    workflow_version_number: int
    workflow_name: str
    workflow_definition: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.workflow_version_number < 1:
            raise AgentValidationError("workflow version number must be positive")
        if not self.workflow_name.strip():
            raise AgentValidationError("workflow name must not be blank")
