from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_export_openapi_script_writes_schema(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[3]
    output_path = tmp_path / "openapi.json"

    result = subprocess.run(
        ["uv", "run", "python", "scripts/export_openapi.py", "--output", str(output_path)],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    schema = json.loads(output_path.read_text(encoding="utf-8"))
    assert schema["info"]["title"] == "Hify API"
    assert "/runs/{run_id}/diagnostics" in schema["paths"]
    assert "/usage/cost-summary" in schema["paths"]
    assert "/providers/models/{model_id}/pricing" in schema["paths"]
    assert "ErrorResponse" in schema["components"]["schemas"]


def test_openapi_operation_ids_are_stable_and_unique() -> None:
    schema = load_generated_openapi_schema()

    operation_ids = [
        operation["operationId"]
        for path_item in schema["paths"].values()
        for operation in path_item.values()
    ]
    assert len(operation_ids) == len(set(operation_ids))
    assert "runs_get_run" in operation_ids
    assert "providers_set_provider_model_pricing" in operation_ids
    assert "health_live" in operation_ids
    assert "health_ready" in operation_ids
    assert "healthz" in operation_ids


def test_openapi_error_response_contract_is_documented() -> None:
    schema = load_generated_openapi_schema()

    error_detail = schema["components"]["schemas"]["ErrorDetailResponse"]
    assert set(error_detail["properties"]) == {"code", "message", "metadata"}
    run_get_responses = schema["paths"]["/runs/{run_id}"]["get"]["responses"]
    assert run_get_responses["403"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ErrorResponse"
    )


def load_generated_openapi_schema() -> dict[str, object]:
    backend_root = Path(__file__).resolve().parents[3]
    output_path = (
        backend_root.parent / "apps" / "web" / "src" / "lib" / "api" / "generated" / "openapi.json"
    )
    return json.loads(output_path.read_text(encoding="utf-8"))
