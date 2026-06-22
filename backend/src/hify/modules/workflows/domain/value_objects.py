from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping
from uuid import UUID

from hify.modules.workflows.domain.errors import WorkflowValidationError

MAX_WORKFLOW_NAME_LENGTH = 120
MAX_WORKFLOW_DESCRIPTION_LENGTH = 500
MAX_WORKFLOW_NODES = 50
MAX_WORKFLOW_EDGES = 100


class WorkflowStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class WorkflowNodeKind(StrEnum):
    START = "start"
    LLM = "llm"
    TOOL = "tool"
    END = "end"


@dataclass(frozen=True, slots=True)
class WorkflowDefinitionIssue:
    code: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class WorkflowDefinitionValidation:
    issues: tuple[WorkflowDefinitionIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not self.issues


def default_workflow_definition() -> dict[str, object]:
    return {
        "nodes": [
            {"id": "start", "kind": WorkflowNodeKind.START.value, "config": {}},
            {"id": "end", "kind": WorkflowNodeKind.END.value, "config": {}},
        ],
        "edges": [{"source_node_id": "start", "target_node_id": "end"}],
    }


def normalize_workflow_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise WorkflowValidationError("workflow name must not be blank")
    if len(normalized) > MAX_WORKFLOW_NAME_LENGTH:
        raise WorkflowValidationError("workflow name is too long")
    return normalized


def normalize_workflow_description(description: str | None) -> str | None:
    if description is None:
        return None
    normalized = description.strip()
    if not normalized:
        return None
    if len(normalized) > MAX_WORKFLOW_DESCRIPTION_LENGTH:
        raise WorkflowValidationError("workflow description is too long")
    return normalized


def normalize_workflow_definition(definition: Mapping[str, object]) -> dict[str, object]:
    copied = deepcopy(dict(definition))
    _ensure_json_value(copied, path="$")
    return copied


def validate_workflow_definition(
    definition: Mapping[str, object],
) -> WorkflowDefinitionValidation:
    issues: list[WorkflowDefinitionIssue] = []
    nodes_value = definition.get("nodes")
    edges_value = definition.get("edges")
    if not isinstance(nodes_value, list):
        issues.append(_issue("missing_nodes", "$.nodes", "workflow definition requires nodes list"))
        nodes: list[object] = []
    else:
        nodes = nodes_value
    if not isinstance(edges_value, list):
        issues.append(_issue("missing_edges", "$.edges", "workflow definition requires edges list"))
        edges: list[object] = []
    else:
        edges = edges_value

    if len(nodes) > MAX_WORKFLOW_NODES:
        issues.append(_issue("too_many_nodes", "$.nodes", "workflow has too many nodes"))
    if len(edges) > MAX_WORKFLOW_EDGES:
        issues.append(_issue("too_many_edges", "$.edges", "workflow has too many edges"))

    node_ids: set[str] = set()
    node_kinds: dict[str, WorkflowNodeKind] = {}
    start_node_ids: list[str] = []
    end_node_ids: list[str] = []
    for index, node in enumerate(nodes):
        path = f"$.nodes[{index}]"
        if not isinstance(node, dict):
            issues.append(_issue("invalid_node", path, "node must be an object"))
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            issues.append(_issue("invalid_node_id", f"{path}.id", "node id must be a nonblank string"))
            continue
        if node_id in node_ids:
            issues.append(_issue("duplicate_node_id", f"{path}.id", "node id must be unique"))
            continue
        node_ids.add(node_id)
        kind_value = node.get("kind")
        try:
            node_kind = WorkflowNodeKind(str(kind_value))
        except ValueError:
            issues.append(_issue("invalid_node_kind", f"{path}.kind", "node kind is not supported"))
            continue
        node_kinds[node_id] = node_kind
        if node_kind is WorkflowNodeKind.START:
            start_node_ids.append(node_id)
        elif node_kind is WorkflowNodeKind.END:
            end_node_ids.append(node_id)
        elif node_kind is WorkflowNodeKind.LLM:
            _validate_uuid_config(node, "provider_model_id", f"{path}.config", issues)
        elif node_kind is WorkflowNodeKind.TOOL:
            _validate_uuid_config(node, "tool_id", f"{path}.config", issues)

    if len(start_node_ids) != 1:
        issues.append(_issue("invalid_start_count", "$.nodes", "workflow requires exactly one start node"))
    if not end_node_ids:
        issues.append(_issue("missing_end", "$.nodes", "workflow requires at least one end node"))

    outgoing: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    incoming: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    for index, edge in enumerate(edges):
        path = f"$.edges[{index}]"
        if not isinstance(edge, dict):
            issues.append(_issue("invalid_edge", path, "edge must be an object"))
            continue
        source_node_id = edge.get("source_node_id")
        target_node_id = edge.get("target_node_id")
        if not isinstance(source_node_id, str) or source_node_id not in node_ids:
            issues.append(
                _issue("invalid_edge_source", f"{path}.source_node_id", "edge source node is unknown")
            )
            continue
        if not isinstance(target_node_id, str) or target_node_id not in node_ids:
            issues.append(
                _issue("invalid_edge_target", f"{path}.target_node_id", "edge target node is unknown")
            )
            continue
        if source_node_id == target_node_id:
            issues.append(_issue("self_edge", path, "edge must not point to the same node"))
            continue
        outgoing[source_node_id].add(target_node_id)
        incoming[target_node_id].add(source_node_id)

    for start_node_id in start_node_ids:
        if incoming[start_node_id]:
            issues.append(_issue("start_has_incoming", "$.edges", "start node must not have incoming edges"))
    for end_node_id in end_node_ids:
        if outgoing[end_node_id]:
            issues.append(_issue("end_has_outgoing", "$.edges", "end node must not have outgoing edges"))

    if start_node_ids and not _has_graph_shape_issue(issues):
        reachable = _reachable_from(start_node_ids[0], outgoing)
        for node_id in sorted(node_ids - reachable):
            issues.append(_issue("unreachable_node", "$.edges", f"node {node_id} is not reachable"))
        reverse_reachable = set().union(*(_reachable_from(end_node_id, incoming) for end_node_id in end_node_ids))
        for node_id in sorted(node_ids - reverse_reachable):
            issues.append(_issue("dead_end_node", "$.edges", f"node {node_id} cannot reach an end node"))

    return WorkflowDefinitionValidation(issues=tuple(issues))


def collect_model_ids(definition: Mapping[str, object]) -> tuple[UUID, ...]:
    return _collect_uuid_config_values(definition, WorkflowNodeKind.LLM, "provider_model_id")


def collect_tool_ids(definition: Mapping[str, object]) -> tuple[UUID, ...]:
    return _collect_uuid_config_values(definition, WorkflowNodeKind.TOOL, "tool_id")


def _ensure_json_value(value: object, *, path: str) -> None:
    if value is None or isinstance(value, str | int | float | bool):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _ensure_json_value(item, path=f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise WorkflowValidationError("workflow definition object keys must be strings")
            _ensure_json_value(item, path=f"{path}.{key}")
        return
    raise WorkflowValidationError(
        "workflow definition must be JSON serializable",
        metadata={"path": path},
    )


def _validate_uuid_config(
    node: Mapping[str, object],
    field_name: str,
    path: str,
    issues: list[WorkflowDefinitionIssue],
) -> None:
    config = node.get("config")
    if not isinstance(config, dict):
        issues.append(_issue("invalid_node_config", path, "node config must be an object"))
        return
    field_value = config.get(field_name)
    if not isinstance(field_value, str):
        issues.append(_issue("missing_node_reference", f"{path}.{field_name}", "node reference is required"))
        return
    try:
        UUID(field_value)
    except ValueError:
        issues.append(_issue("invalid_node_reference", f"{path}.{field_name}", "node reference must be a UUID"))


def _collect_uuid_config_values(
    definition: Mapping[str, object],
    node_kind: WorkflowNodeKind,
    field_name: str,
) -> tuple[UUID, ...]:
    nodes = definition.get("nodes")
    if not isinstance(nodes, list):
        return ()
    values: list[UUID] = []
    for node in nodes:
        if not isinstance(node, dict) or node.get("kind") != node_kind.value:
            continue
        config = node.get("config")
        if not isinstance(config, dict):
            continue
        field_value = config.get(field_name)
        if isinstance(field_value, str):
            try:
                values.append(UUID(field_value))
            except ValueError:
                continue
    return tuple(dict.fromkeys(values))


def _reachable_from(start_node_id: str, outgoing: Mapping[str, set[str]]) -> set[str]:
    visited: set[str] = set()
    pending = [start_node_id]
    while pending:
        node_id = pending.pop()
        if node_id in visited:
            continue
        visited.add(node_id)
        pending.extend(sorted(outgoing.get(node_id, set()) - visited))
    return visited


def _has_graph_shape_issue(issues: list[WorkflowDefinitionIssue]) -> bool:
    return any(
        issue.code
        in {
            "missing_nodes",
            "missing_edges",
            "invalid_node",
            "invalid_node_id",
            "duplicate_node_id",
            "invalid_node_kind",
            "invalid_start_count",
            "missing_end",
            "invalid_edge",
            "invalid_edge_source",
            "invalid_edge_target",
            "self_edge",
        }
        for issue in issues
    )


def _issue(code: str, path: str, message: str) -> WorkflowDefinitionIssue:
    return WorkflowDefinitionIssue(code=code, path=path, message=message)
