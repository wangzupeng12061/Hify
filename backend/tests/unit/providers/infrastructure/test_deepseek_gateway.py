from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Any, cast
from uuid import UUID

import pytest

from hify.modules.providers.contracts.dto import (
    CallContext,
    DoneChunk,
    ModelMessage,
    ModelRequest,
    ModelUsage,
    TextDeltaChunk,
    UsageChunk,
)
from hify.modules.providers.contracts.errors import ProviderBadRequestError
from hify.modules.providers.domain.entities import ModelProvider, ProviderCredential, ProviderModel
from hify.modules.providers.domain.value_objects import (
    CredentialSecret,
    CredentialStatus,
    ModelKind,
    ModelStatus,
    ProviderStatus,
    ProviderType,
)
from hify.modules.providers.infrastructure.adapters.deepseek.gateway import (
    DEEPSEEK_DEFAULT_BASE_URL,
    DeepSeekClientRegistry,
    DeepSeekModelGateway,
)

TEAM_ID = UUID("00000000-0000-7000-8000-000000000001")
USER_ID = UUID("00000000-0000-7000-8000-000000000002")
PROVIDER_ID = UUID("00000000-0000-7000-8000-000000000003")
MODEL_ID = UUID("00000000-0000-7000-8000-000000000004")


async def test_deepseek_gateway_streams_hify_chunks_and_uses_runtime_credentials() -> None:
    client = FakeOpenAIClient(
        (
            FakeChunk(choices=(FakeChoice(delta=FakeDelta(content="hel")),)),
            FakeChunk(choices=(FakeChoice(delta=FakeDelta(content="lo"), finish_reason="stop"),)),
            FakeChunk(usage=FakeUsage(prompt_tokens=3, completion_tokens=5)),
        )
    )
    registry = RecordingClientRegistry(client)
    gateway = DeepSeekModelGateway(
        FakeUnitOfWorkFactory(provider_type=ProviderType.DEEPSEEK),
        FakeCredentialDecryptor(),
        client_registry=cast(DeepSeekClientRegistry, registry),
    )

    chunks = tuple([chunk async for chunk in gateway.stream(_request(), _context())])

    assert chunks == (
        TextDeltaChunk(chunk_type="text_delta", text="hel"),
        TextDeltaChunk(chunk_type="text_delta", text="lo"),
        DoneChunk(chunk_type="done", finish_reason="stop"),
        UsageChunk(
            chunk_type="usage",
            usage=ModelUsage(input_tokens=3, output_tokens=5),
        ),
    )
    assert registry.runtime_model is not None
    assert registry.runtime_model.api_key == "decrypted-secret"
    assert registry.runtime_model.base_url == DEEPSEEK_DEFAULT_BASE_URL
    assert client.requests == [
        {
            "model": "deepseek-v4-flash",
            "messages": [
                {"role": "system", "content": "You are Hify."},
                {"role": "user", "content": "Hello"},
            ],
            "stream": True,
            "stream_options": {"include_usage": True},
        }
    ]


async def test_deepseek_gateway_rejects_non_deepseek_models() -> None:
    gateway = DeepSeekModelGateway(
        FakeUnitOfWorkFactory(provider_type=ProviderType.OPENAI),
        FakeCredentialDecryptor(),
        client_registry=cast(DeepSeekClientRegistry, RecordingClientRegistry(FakeOpenAIClient(()))),
    )

    with pytest.raises(ProviderBadRequestError):
        tuple([chunk async for chunk in gateway.stream(_request(), _context())])


class FakeCancellationToken:
    def is_cancelled(self) -> bool:
        return False

    def raise_if_cancelled(self) -> None:
        return None


class FakeCredentialDecryptor:
    def decrypt(self, secret: CredentialSecret) -> str:
        _ = secret
        return "decrypted-secret"


class RecordingClientRegistry:
    def __init__(self, client: FakeOpenAIClient) -> None:
        self._client = client
        self.runtime_model: Any | None = None

    def get_client(self, runtime_model: Any) -> FakeOpenAIClient:
        self.runtime_model = runtime_model
        return self._client


class FakeOpenAIClient:
    def __init__(self, chunks: tuple[FakeChunk, ...]) -> None:
        self.requests: list[dict[str, object]] = []
        self.chat = FakeChat(FakeCompletions(chunks, self.requests))


class FakeChat:
    def __init__(self, completions: FakeCompletions) -> None:
        self.completions = completions


class FakeCompletions:
    def __init__(self, chunks: tuple[FakeChunk, ...], requests: list[dict[str, object]]) -> None:
        self._chunks = chunks
        self._requests = requests

    async def create(self, **body: object) -> FakeStream:
        self._requests.append(body)
        return FakeStream(self._chunks)


class FakeStream:
    def __init__(self, chunks: tuple[FakeChunk, ...]) -> None:
        self._chunks = chunks

    def __aiter__(self) -> AsyncIterator[FakeChunk]:
        return self._stream()

    async def _stream(self) -> AsyncIterator[FakeChunk]:
        for chunk in self._chunks:
            yield chunk


@dataclass(frozen=True, slots=True)
class FakeUsage:
    prompt_tokens: int
    completion_tokens: int


@dataclass(frozen=True, slots=True)
class FakeDelta:
    content: str | None = None


@dataclass(frozen=True, slots=True)
class FakeChoice:
    delta: FakeDelta
    finish_reason: str | None = None


@dataclass(frozen=True, slots=True)
class FakeChunk:
    choices: tuple[FakeChoice, ...] = ()
    usage: FakeUsage | None = None


class FakeUnitOfWorkFactory:
    def __init__(self, *, provider_type: ProviderType) -> None:
        now = datetime(2026, 6, 24, tzinfo=UTC)
        self.provider = ModelProvider(
            id=PROVIDER_ID,
            team_id=TEAM_ID,
            provider_type=provider_type,
            name="DeepSeek",
            base_url=None,
            status=ProviderStatus.ACTIVE,
            version=0,
            created_by=USER_ID,
            created_at=now,
            updated_at=now,
        )
        self.model = ProviderModel(
            id=MODEL_ID,
            team_id=TEAM_ID,
            provider_id=PROVIDER_ID,
            model_name="deepseek-v4-flash",
            display_name="DeepSeek V4 Flash",
            kind=ModelKind.CHAT,
            status=ModelStatus.ACTIVE,
            context_window_tokens=128000,
            supports_tools=False,
            supports_vision=False,
            supports_structured_output=False,
            price_per_1m_input_tokens=None,
            price_per_1m_output_tokens=None,
            version=0,
            created_at=now,
            updated_at=now,
        )
        self.credential = ProviderCredential(
            id=UUID("00000000-0000-7000-8000-000000000005"),
            team_id=TEAM_ID,
            provider_id=PROVIDER_ID,
            secret=CredentialSecret(
                ciphertext=b"encrypted-secret",
                key_version=1,
                fingerprint="fingerprint",
            ),
            status=CredentialStatus.ACTIVE,
            version=0,
            created_at=now,
            updated_at=now,
        )

    def __call__(self) -> FakeUnitOfWork:
        return FakeUnitOfWork(self.provider, self.model, self.credential)


class FakeUnitOfWork:
    def __init__(
        self,
        provider: ModelProvider,
        model: ProviderModel,
        credential: ProviderCredential,
    ) -> None:
        self.providers = FakeProviderRepository(provider)
        self.models = FakeModelRepository(model)
        self.credentials = FakeCredentialRepository(credential)

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeProviderRepository:
    def __init__(self, provider: ModelProvider) -> None:
        self._provider = provider

    async def get_by_id(self, provider_id: UUID) -> ModelProvider | None:
        if provider_id == self._provider.id:
            return self._provider
        return None


class FakeModelRepository:
    def __init__(self, model: ProviderModel) -> None:
        self._model = model

    async def get_by_id(self, model_id: UUID) -> ProviderModel | None:
        if model_id == self._model.id:
            return self._model
        return None


class FakeCredentialRepository:
    def __init__(self, credential: ProviderCredential) -> None:
        self._credential = credential

    async def get_by_provider_id(self, provider_id: UUID) -> ProviderCredential | None:
        if provider_id == self._credential.provider_id:
            return self._credential
        return None


def _request() -> ModelRequest:
    return ModelRequest(
        model_id=MODEL_ID,
        system_prompt="You are Hify.",
        messages=(ModelMessage(role="user", content="Hello"),),
    )


def _context() -> CallContext:
    return CallContext(
        run_id=UUID("00000000-0000-7000-8000-000000000006"),
        attempt_id=UUID("00000000-0000-7000-8000-000000000007"),
        team_id=TEAM_ID,
        user_id=USER_ID,
        deadline=monotonic() + 60,
        cancellation=FakeCancellationToken(),
    )
