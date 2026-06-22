from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from hify.modules.agents.domain.entities import Agent
from hify.modules.agents.domain.errors import AgentValidationError
from hify.modules.agents.domain.value_objects import AgentStatus, ModelBindingSnapshot


def test_create_agent_normalizes_fields() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)

    agent = Agent.create(
        team_id=UUID("00000000-0000-7000-8000-000000000001"),
        name="  Support   Bot ",
        description="  Answers   questions ",
        system_prompt="  You are helpful. ",
        provider_model_id=UUID("00000000-0000-7000-8000-000000000002"),
        created_by=UUID("00000000-0000-7000-8000-000000000003"),
        now=now,
    )

    assert agent.name == "Support Bot"
    assert agent.description == "Answers questions"
    assert agent.system_prompt == "You are helpful."
    assert agent.status == AgentStatus.DRAFT
    assert agent.latest_version_number == 0


def test_publish_agent_creates_immutable_version_snapshot() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)
    agent = Agent.create(
        team_id=UUID("00000000-0000-7000-8000-000000000001"),
        name="Support Bot",
        description=None,
        system_prompt="You are helpful.",
        provider_model_id=UUID("00000000-0000-7000-8000-000000000002"),
        created_by=UUID("00000000-0000-7000-8000-000000000003"),
        now=now,
    )
    model_snapshot = ModelBindingSnapshot(
        provider_model_id=agent.provider_model_id,
        provider_type="openai",
        provider_name="OpenAI",
        model_name="gpt-4.1",
        model_display_name="GPT 4.1",
        context_window_tokens=128000,
        supports_tools=True,
        supports_vision=True,
        supports_structured_output=True,
    )

    version = agent.publish(
        model_snapshot=model_snapshot,
        published_by=UUID("00000000-0000-7000-8000-000000000003"),
        now=now,
    )

    assert agent.status == AgentStatus.PUBLISHED
    assert agent.latest_version_number == 1
    assert version.version_number == 1
    assert version.model_name == "gpt-4.1"
    assert version.system_prompt == "You are helpful."


def test_model_binding_snapshot_rejects_invalid_context_window() -> None:
    with pytest.raises(AgentValidationError, match="context window"):
        ModelBindingSnapshot(
            provider_model_id=UUID("00000000-0000-7000-8000-000000000002"),
            provider_type="openai",
            provider_name="OpenAI",
            model_name="gpt-4.1",
            model_display_name="GPT 4.1",
            context_window_tokens=0,
            supports_tools=True,
            supports_vision=True,
            supports_structured_output=True,
        )
