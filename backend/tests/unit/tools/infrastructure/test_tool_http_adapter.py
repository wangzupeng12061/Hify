from __future__ import annotations

from uuid import UUID

import httpx
import pytest

from hify.modules.tools.application.ports import HttpToolInvocation
from hify.modules.tools.domain.errors import (
    ToolExecutionHttpError,
    ToolExecutionResponseTooLargeError,
    ToolExecutionTimeoutError,
)
from hify.modules.tools.infrastructure.adapters.http import HttpxToolInvoker


@pytest.mark.asyncio
async def test_http_tool_invoker_posts_arguments_and_returns_text() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["X-Hify-Tool"] == "crm"
        assert request.content == b'{"email":"owner@example.com"}'
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json", "Authorization": "secret"},
            content=b'{"name":"Owner"}',
        )

    invoker = HttpxToolInvoker(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    result = await invoker.invoke_http_tool(_invocation())

    assert result.content == '{"name":"Owner"}'
    assert result.metadata == {
        "status_code": 200,
        "headers": {"content-type": "application/json", "content-length": "16"},
    }


@pytest.mark.asyncio
async def test_http_tool_invoker_uses_query_params_for_get() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.params["email"] == "owner@example.com"
        return httpx.Response(200, content=b"ok")

    invoker = HttpxToolInvoker(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    result = await invoker.invoke_http_tool(_invocation(http_method="GET"))

    assert result.content == "ok"


@pytest.mark.asyncio
async def test_http_tool_invoker_maps_error_status() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"failure")

    invoker = HttpxToolInvoker(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    with pytest.raises(ToolExecutionHttpError):
        await invoker.invoke_http_tool(_invocation())


@pytest.mark.asyncio
async def test_http_tool_invoker_maps_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    invoker = HttpxToolInvoker(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    with pytest.raises(ToolExecutionTimeoutError):
        await invoker.invoke_http_tool(_invocation())


@pytest.mark.asyncio
async def test_http_tool_invoker_rejects_large_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"too large")

    invoker = HttpxToolInvoker(
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        max_response_bytes=3,
    )

    with pytest.raises(ToolExecutionResponseTooLargeError):
        await invoker.invoke_http_tool(_invocation())


def _invocation(http_method: str = "POST") -> HttpToolInvocation:
    return HttpToolInvocation(
        team_id=UUID("00000000-0000-7000-8000-000000000001"),
        tool_id=UUID("00000000-0000-7000-8000-000000000002"),
        tool_call_id=UUID("00000000-0000-7000-8000-000000000003"),
        endpoint_url="https://crm.example.com/search",
        http_method=http_method,
        http_headers={"X-Hify-Tool": "crm"},
        arguments={"email": "owner@example.com"},
    )
