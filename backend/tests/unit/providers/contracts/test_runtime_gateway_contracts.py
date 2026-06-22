from __future__ import annotations

from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest

from hify.modules.providers.contracts.dto import ModelMessage, ModelRequest, ModelUsage
from hify.modules.providers.contracts.errors import ProviderRateLimitError, ProviderTimeoutError


def test_model_request_is_immutable_and_uses_messages() -> None:
    request = ModelRequest(
        model_id=UUID("00000000-0000-7000-8000-000000000001"),
        messages=(ModelMessage(role="user", content="Hello"),),
        system_prompt="You are helpful.",
    )

    assert request.messages[0].content == "Hello"
    with pytest.raises(FrozenInstanceError):
        request.system_prompt = None  # type: ignore[misc]


def test_model_usage_calculates_total_tokens() -> None:
    usage = ModelUsage(input_tokens=3, output_tokens=5)

    assert usage.total_tokens == 8


def test_runtime_errors_expose_stable_metadata() -> None:
    rate_limit_error = ProviderRateLimitError("limited", retry_after_seconds=1.5)
    timeout_error = ProviderTimeoutError("timeout", timeout_stage="first_token")

    assert rate_limit_error.to_detail().code == "PROVIDER_RATE_LIMIT_ERROR"
    assert rate_limit_error.to_detail().metadata == {"retry_after_seconds": 1.5}
    assert timeout_error.to_detail().metadata == {"timeout_stage": "first_token"}
