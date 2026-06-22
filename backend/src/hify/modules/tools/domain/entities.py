from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from uuid import UUID

from hify.modules.tools.domain.errors import ToolValidationError
from hify.modules.tools.domain.value_objects import (
    HttpToolMethod,
    ToolKind,
    ToolStatus,
    normalize_builtin_name,
    normalize_endpoint_url,
    normalize_http_headers,
    normalize_input_schema,
    normalize_tool_description,
    normalize_tool_name,
)
from hify.shared.domain.ids import new_uuid


@dataclass(slots=True)
class ToolDefinition:
    id: UUID
    team_id: UUID
    name: str
    description: str | None
    tool_kind: ToolKind
    status: ToolStatus
    input_schema: Mapping[str, object]
    builtin_name: str | None
    endpoint_url: str | None
    http_method: HttpToolMethod | None
    http_headers: Mapping[str, str]
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        name: str,
        description: str | None,
        tool_kind: ToolKind,
        input_schema: Mapping[str, object],
        builtin_name: str | None,
        endpoint_url: str | None,
        http_method: HttpToolMethod | None,
        http_headers: Mapping[str, str] | None,
        created_by: UUID,
        now: datetime,
    ) -> ToolDefinition:
        normalized_builtin_name = normalize_builtin_name(builtin_name)
        normalized_endpoint_url = normalize_endpoint_url(endpoint_url)
        normalized_http_headers = normalize_http_headers(http_headers)
        _validate_kind_fields(
            tool_kind=tool_kind,
            builtin_name=normalized_builtin_name,
            endpoint_url=normalized_endpoint_url,
            http_method=http_method,
        )
        return cls(
            id=new_uuid(),
            team_id=team_id,
            name=normalize_tool_name(name),
            description=normalize_tool_description(description),
            tool_kind=tool_kind,
            status=ToolStatus.ACTIVE,
            input_schema=normalize_input_schema(input_schema),
            builtin_name=normalized_builtin_name,
            endpoint_url=normalized_endpoint_url,
            http_method=http_method,
            http_headers=normalized_http_headers,
            version=0,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

    def disable(self, *, now: datetime) -> None:
        if self.status is ToolStatus.DISABLED:
            return
        self.status = ToolStatus.DISABLED
        self._mark_updated(now)

    def _mark_updated(self, now: datetime) -> None:
        self.version += 1
        self.updated_at = now


def _validate_kind_fields(
    *,
    tool_kind: ToolKind,
    builtin_name: str | None,
    endpoint_url: str | None,
    http_method: HttpToolMethod | None,
) -> None:
    if tool_kind is ToolKind.BUILTIN:
        if builtin_name is None:
            raise ToolValidationError("builtin tools require a builtin name")
        if endpoint_url is not None or http_method is not None:
            raise ToolValidationError("builtin tools must not define http fields")
        return

    if tool_kind is ToolKind.HTTP:
        if endpoint_url is None:
            raise ToolValidationError("http tools require an endpoint url")
        if http_method is None:
            raise ToolValidationError("http tools require an http method")
        if builtin_name is not None:
            raise ToolValidationError("http tools must not define a builtin name")
