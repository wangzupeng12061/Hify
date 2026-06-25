from __future__ import annotations

from uuid import UUID

import httpx
import pytest

from hify.modules.tools.application.ports import BuiltinToolInvocation
from hify.modules.tools.domain.errors import ToolValidationError
from hify.modules.tools.infrastructure.adapters.web_search import (
    DuckDuckGoWebSearchTool,
)


@pytest.mark.asyncio
async def test_web_search_tool_returns_structured_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["q"] == "ceph latest release"
        if request.url.path == "/":
            return httpx.Response(
                200,
                json={
                    "Heading": "Ceph",
                    "AbstractText": "Ceph is a distributed storage system.",
                    "AbstractURL": "https://ceph.io/",
                    "RelatedTopics": [
                        {
                            "Text": "Ceph Releases - Reef and Squid release notes.",
                            "FirstURL": "https://docs.ceph.com/en/latest/releases/",
                        }
                    ],
                },
            )
        raise AssertionError(f"unexpected request path: {request.url.path}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tool = DuckDuckGoWebSearchTool(client, default_max_results=2)

    result = await tool.invoke(
        BuiltinToolInvocation(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            tool_id=UUID("00000000-0000-7000-8000-000000000002"),
            tool_call_id=UUID("00000000-0000-7000-8000-000000000003"),
            builtin_name="web.search",
            arguments={"query": "ceph latest release"},
        )
    )

    assert result.metadata == {
        "provider": "duckduckgo",
        "result_count": 2,
        "has_answer": True,
    }
    assert "Ceph is a distributed storage system." in result.content
    assert "https://docs.ceph.com/en/latest/releases/" in result.content


@pytest.mark.asyncio
async def test_web_search_tool_falls_back_to_html_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["q"] == "ceph squid latest release"
        if request.url.path == "/":
            return httpx.Response(200, json={"Heading": "", "RelatedTopics": []})
        if request.url.path == "/html/":
            return httpx.Response(
                200,
                text="""
                <html>
                  <body>
                    <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fdocs.ceph.com%2Fen%2Flatest%2Freleases%2Fsquid%2F">Ceph Squid Releases</a>
                    <a class="result__snippet">Squid release notes and versions.</a>
                    <a class="result__a" href="https://ceph.io/en/news/">Ceph News</a>
                    <div class="result__snippet">Latest Ceph project news.</div>
                  </body>
                </html>
                """,
            )
        raise AssertionError(f"unexpected request path: {request.url.path}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tool = DuckDuckGoWebSearchTool(client, default_max_results=2)

    result = await tool.invoke(
        BuiltinToolInvocation(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            tool_id=UUID("00000000-0000-7000-8000-000000000002"),
            tool_call_id=UUID("00000000-0000-7000-8000-000000000003"),
            builtin_name="web.search",
            arguments={"query": "ceph squid latest release"},
        )
    )

    assert result.metadata["result_count"] == 2
    assert "Ceph Squid Releases" in result.content
    assert "https://docs.ceph.com/en/latest/releases/squid/" in result.content
    assert "Squid release notes and versions." in result.content


@pytest.mark.asyncio
async def test_web_search_tool_requires_query() -> None:
    tool = DuckDuckGoWebSearchTool(httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200))))

    with pytest.raises(ToolValidationError):
        await tool.invoke(
            BuiltinToolInvocation(
                team_id=UUID("00000000-0000-7000-8000-000000000001"),
                tool_id=UUID("00000000-0000-7000-8000-000000000002"),
                tool_call_id=UUID("00000000-0000-7000-8000-000000000003"),
                builtin_name="web.search",
                arguments={},
            )
        )
