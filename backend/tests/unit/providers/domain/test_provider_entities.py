from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from hify.modules.providers.domain.entities import ModelProvider, ProviderModel
from hify.modules.providers.domain.errors import ProviderValidationError
from hify.modules.providers.domain.value_objects import (
    CredentialSecret,
    ModelKind,
    ProviderType,
)


def test_create_provider_normalizes_name_and_base_url() -> None:
    provider = ModelProvider.create(
        team_id=UUID("00000000-0000-7000-8000-000000000001"),
        provider_type=ProviderType.OPENAI,
        name="  Main   OpenAI ",
        base_url="https://api.openai.com/",
        created_by=UUID("00000000-0000-7000-8000-000000000002"),
        now=datetime(2026, 6, 22, tzinfo=UTC),
    )

    assert provider.name == "Main OpenAI"
    assert provider.base_url == "https://api.openai.com"
    assert provider.version == 0


def test_credential_secret_rejects_missing_ciphertext() -> None:
    with pytest.raises(ProviderValidationError, match="ciphertext"):
        CredentialSecret(ciphertext=b"", key_version=1, fingerprint="abc")


def test_create_model_rejects_non_positive_context_window() -> None:
    with pytest.raises(ProviderValidationError, match="context window"):
        ProviderModel.create(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            provider_id=UUID("00000000-0000-7000-8000-000000000002"),
            model_name="gpt-4.1",
            display_name="GPT 4.1",
            kind=ModelKind.CHAT,
            context_window_tokens=0,
            supports_tools=True,
            supports_vision=False,
            supports_structured_output=True,
            now=datetime(2026, 6, 22, tzinfo=UTC),
        )
