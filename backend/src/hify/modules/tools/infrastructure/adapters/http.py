from __future__ import annotations

from collections.abc import Mapping

import httpx

from hify.modules.tools.application.ports import HttpToolInvocation
from hify.modules.tools.contracts.dto import ToolExecutionResult
from hify.modules.tools.domain.errors import (
    ToolExecutionHttpError,
    ToolExecutionResponseTooLargeError,
    ToolExecutionTimeoutError,
)

DEFAULT_HTTP_TOOL_TIMEOUT_SECONDS = 15.0
DEFAULT_HTTP_TOOL_MAX_RESPONSE_BYTES = 256 * 1024
SAFE_RESPONSE_HEADERS = frozenset({"content-type", "content-length"})


class HttpxToolInvoker:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        timeout_seconds: float = DEFAULT_HTTP_TOOL_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_HTTP_TOOL_MAX_RESPONSE_BYTES,
    ) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        self._max_response_bytes = max_response_bytes

    async def invoke_http_tool(self, invocation: HttpToolInvocation) -> ToolExecutionResult:
        try:
            response = await self._client.request(
                invocation.http_method,
                invocation.endpoint_url,
                headers=dict(invocation.http_headers),
                params=_query_params(invocation.arguments)
                if invocation.http_method in {"GET", "DELETE"}
                else None,
                json=dict(invocation.arguments)
                if invocation.http_method not in {"GET", "DELETE"}
                else None,
            )
        except httpx.TimeoutException as exc:
            raise ToolExecutionTimeoutError("http tool timed out") from exc
        except httpx.HTTPError as exc:
            raise ToolExecutionHttpError("http tool request failed") from exc

        content = response.content
        if len(content) > self._max_response_bytes:
            raise ToolExecutionResponseTooLargeError(
                "http tool response is too large",
                metadata={
                    "size_bytes": len(content),
                    "max_size_bytes": self._max_response_bytes,
                },
            )
        if response.status_code >= 400:
            raise ToolExecutionHttpError(
                "http tool returned an error status",
                metadata={"status_code": response.status_code},
            )

        return ToolExecutionResult(
            tool_call_id=invocation.tool_call_id,
            content=_decode_content(content, response),
            metadata={
                "status_code": response.status_code,
                "headers": _safe_response_headers(response.headers),
            },
        )


def _decode_content(content: bytes, response: httpx.Response) -> str:
    encoding = response.encoding or "utf-8"
    return content.decode(encoding, errors="replace")


def _query_params(arguments: Mapping[str, object]) -> dict[str, str]:
    params: dict[str, str] = {}
    for name, value in arguments.items():
        if value is None:
            continue
        params[name] = str(value)
    return params


def _safe_response_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        name.lower(): value
        for name, value in headers.items()
        if name.lower() in SAFE_RESPONSE_HEADERS
    }
