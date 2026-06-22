from __future__ import annotations

from collections.abc import Awaitable, Callable

from hify.modules.tools.application.ports import BuiltinToolInvocation
from hify.modules.tools.contracts.dto import ToolExecutionResult
from hify.modules.tools.domain.errors import ToolExecutorNotConfiguredError

BuiltinToolHandler = Callable[[BuiltinToolInvocation], Awaitable[ToolExecutionResult]]


class EmptyBuiltinToolInvoker:
    def __init__(self, handlers: dict[str, BuiltinToolHandler] | None = None) -> None:
        self._handlers = handlers or {}

    async def invoke_builtin_tool(self, invocation: BuiltinToolInvocation) -> ToolExecutionResult:
        handler = self._handlers.get(invocation.builtin_name)
        if handler is None:
            raise ToolExecutorNotConfiguredError(
                "builtin tool is not configured",
                metadata={"builtin_name": invocation.builtin_name},
            )
        return await handler(invocation)
