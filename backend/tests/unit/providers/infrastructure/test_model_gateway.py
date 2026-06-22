from __future__ import annotations

from time import monotonic
from uuid import UUID

import pytest

from hify.modules.providers.contracts.dto import (
    CallContext,
    DoneChunk,
    ModelMessage,
    ModelRequest,
    TextDeltaChunk,
    UsageChunk,
    ModelUsage,
)
from hify.modules.providers.contracts.errors import (
    ProviderCancelledError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from hify.modules.providers.infrastructure.adapters.fake import (
    MissingModelGateway,
    StaticModelGateway,
)


class DummyCancellationToken:
    def __init__(self, *, cancelled: bool = False) -> None:
        self.cancelled = cancelled

    def is_cancelled(self) -> bool:
        return self.cancelled

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise ProviderCancelledError("model call was cancelled")


def test_static_model_gateway_streams_hify_chunks() -> None:
    gateway = StaticModelGateway(
        (
            TextDeltaChunk(chunk_type="text_delta", text="hello"),
            UsageChunk(chunk_type="usage", usage=ModelUsage(input_tokens=1, output_tokens=2)),
            DoneChunk(chunk_type="done", finish_reason="stop"),
        )
    )

    chunks = _collect(gateway.stream(_request(), _context()))

    assert chunks[0] == TextDeltaChunk(chunk_type="text_delta", text="hello")
    assert chunks[1] == UsageChunk(
        chunk_type="usage",
        usage=ModelUsage(input_tokens=1, output_tokens=2),
    )
    assert chunks[2] == DoneChunk(chunk_type="done", finish_reason="stop")


def test_static_model_gateway_respects_cancellation() -> None:
    gateway = StaticModelGateway((TextDeltaChunk(chunk_type="text_delta", text="hello"),))
    context = _context(cancellation=DummyCancellationToken(cancelled=True))

    with pytest.raises(ProviderCancelledError):
        _collect(gateway.stream(_request(), context))


def test_static_model_gateway_respects_deadline() -> None:
    gateway = StaticModelGateway((TextDeltaChunk(chunk_type="text_delta", text="hello"),))
    context = _context(deadline=monotonic() - 1)

    with pytest.raises(ProviderTimeoutError):
        _collect(gateway.stream(_request(), context))


def test_missing_model_gateway_raises_unavailable() -> None:
    gateway = MissingModelGateway()

    with pytest.raises(ProviderUnavailableError):
        _collect(gateway.stream(_request(), _context()))


def _request() -> ModelRequest:
    return ModelRequest(
        model_id=UUID("00000000-0000-7000-8000-000000000001"),
        messages=(ModelMessage(role="user", content="Hello"),),
    )


def _context(
    *,
    cancellation: DummyCancellationToken | None = None,
    deadline: float | None = None,
) -> CallContext:
    return CallContext(
        run_id=UUID("00000000-0000-7000-8000-000000000002"),
        attempt_id=UUID("00000000-0000-7000-8000-000000000003"),
        team_id=UUID("00000000-0000-7000-8000-000000000004"),
        user_id=UUID("00000000-0000-7000-8000-000000000005"),
        deadline=deadline if deadline is not None else monotonic() + 60,
        cancellation=cancellation or DummyCancellationToken(),
    )


def _collect(stream) -> tuple[object, ...]:  # type: ignore[no-untyped-def]
    import asyncio

    async def collect() -> tuple[object, ...]:
        return tuple([chunk async for chunk in stream])

    return asyncio.run(collect())
