from __future__ import annotations

from collections.abc import Mapping

from hify.modules.mcp.contracts.dto import McpToolInvocationRequest
from hify.modules.mcp.contracts.services import McpToolInvoker
from hify.modules.tools.application.ports import (
    BuiltinToolInvocation,
    BuiltinToolInvoker,
    HttpToolInvocation,
    HttpToolInvoker,
    ToolsUnitOfWorkFactory,
)
from hify.modules.tools.contracts.dto import ToolExecutionRequest, ToolExecutionResult
from hify.modules.tools.contracts.services import ToolExecutor
from hify.modules.tools.domain.errors import (
    ToolDisabledError,
    ToolNotFoundError,
    ToolValidationError,
)
from hify.modules.tools.domain.value_objects import ToolKind, ToolStatus


class ToolRuntimeExecutor(ToolExecutor):
    def __init__(
        self,
        unit_of_work_factory: ToolsUnitOfWorkFactory,
        builtin_tool_invoker: BuiltinToolInvoker,
        http_tool_invoker: HttpToolInvoker,
        mcp_tool_invoker: McpToolInvoker,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._builtin_tool_invoker = builtin_tool_invoker
        self._http_tool_invoker = http_tool_invoker
        self._mcp_tool_invoker = mcp_tool_invoker

    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        async with self._unit_of_work_factory() as unit_of_work:
            tool = await unit_of_work.tools.get_by_id(request.tool_id)

        if tool is None or tool.team_id != request.team_id:
            raise ToolNotFoundError("tool was not found")
        if tool.status is not ToolStatus.ACTIVE:
            raise ToolDisabledError("tool is disabled")

        _validate_arguments(tool.input_schema, request.arguments)

        if tool.tool_kind is ToolKind.BUILTIN:
            if tool.builtin_name is None:
                raise ToolValidationError("builtin tool definition is incomplete")
            return await self._builtin_tool_invoker.invoke_builtin_tool(
                BuiltinToolInvocation(
                    team_id=request.team_id,
                    tool_id=request.tool_id,
                    tool_call_id=request.tool_call_id,
                    builtin_name=tool.builtin_name,
                    arguments=request.arguments,
                )
            )

        if tool.tool_kind is ToolKind.HTTP:
            if tool.endpoint_url is None or tool.http_method is None:
                raise ToolValidationError("http tool definition is incomplete")
            return await self._http_tool_invoker.invoke_http_tool(
                HttpToolInvocation(
                    team_id=request.team_id,
                    tool_id=request.tool_id,
                    tool_call_id=request.tool_call_id,
                    endpoint_url=tool.endpoint_url,
                    http_method=tool.http_method.value,
                    http_headers=tool.http_headers,
                    arguments=request.arguments,
                )
            )

        if tool.mcp_server_id is None or tool.mcp_tool_id is None:
            raise ToolValidationError("mcp tool definition is incomplete")
        result = await self._mcp_tool_invoker.invoke_tool(
            McpToolInvocationRequest(
                team_id=request.team_id,
                server_id=tool.mcp_server_id,
                tool_id=tool.mcp_tool_id,
                tool_call_id=request.tool_call_id,
                arguments=request.arguments,
            )
        )
        return ToolExecutionResult(
            tool_call_id=result.tool_call_id,
            content=result.content,
            metadata=result.metadata,
        )


def _validate_arguments(
    input_schema: Mapping[str, object],
    arguments: Mapping[str, object],
) -> None:
    required = input_schema.get("required", [])
    if required is not None and not isinstance(required, list):
        raise ToolValidationError("input schema required field must be a list")

    if isinstance(required, list):
        missing_fields = [
            field_name
            for field_name in required
            if isinstance(field_name, str) and field_name not in arguments
        ]
        if missing_fields:
            raise ToolValidationError(
                "tool arguments are missing required fields",
                metadata={"fields": tuple(missing_fields)},
            )

    properties = input_schema.get("properties")
    if properties is None:
        return
    if not isinstance(properties, dict):
        raise ToolValidationError("input schema properties field must be an object")

    for field_name, field_schema in properties.items():
        if field_name not in arguments:
            continue
        if not isinstance(field_schema, dict):
            continue
        expected_type = field_schema.get("type")
        if isinstance(expected_type, str) and not _matches_json_type(
            arguments[field_name],
            expected_type,
        ):
            raise ToolValidationError(
                "tool argument type is invalid",
                metadata={"field": field_name, "expected_type": expected_type},
            )


def _matches_json_type(value: object, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "null":
        return value is None
    return True
