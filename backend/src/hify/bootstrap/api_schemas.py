from __future__ import annotations

import re
from typing import Any
from typing import Mapping

from fastapi.routing import APIRoute
from pydantic import BaseModel

OPERATION_ID_PART_PATTERN = re.compile(r"[^0-9a-zA-Z_]+")


class ErrorDetailResponse(BaseModel):
    code: str
    message: str
    metadata: Mapping[str, object] | None = None


class ErrorResponse(BaseModel):
    detail: ErrorDetailResponse


DEFAULT_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Bad request"},
    401: {"model": ErrorResponse, "description": "Authentication required"},
    403: {"model": ErrorResponse, "description": "Permission denied"},
    404: {"model": ErrorResponse, "description": "Resource not found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
}


def generate_operation_id(route: APIRoute) -> str:
    route_name = normalize_operation_id_part(route.name)
    if not route.tags:
        return route_name

    route_tag = normalize_operation_id_part(route.tags[0])
    return f"{route_tag}_{route_name}"


def normalize_operation_id_part(value: object) -> str:
    normalized = OPERATION_ID_PART_PATTERN.sub("_", str(value)).strip("_").lower()
    return normalized or "operation"
