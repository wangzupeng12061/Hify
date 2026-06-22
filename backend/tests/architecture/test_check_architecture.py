from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def test_architecture_check_passes() -> None:
    backend_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "scripts/check_architecture.py"],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_architecture_check_rejects_relative_layer_bypass(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[2]
    bad_file = (
        backend_root
        / "src"
        / "hify"
        / "modules"
        / "identity"
        / "api"
        / "_bad_relative_import.py"
    )
    bad_file.write_text("from ..infrastructure import repositories\n")

    try:
        result = subprocess.run(
            [sys.executable, "scripts/check_architecture.py"],
            cwd=backend_root,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        bad_file.unlink(missing_ok=True)
        shutil.rmtree(bad_file.parent / "__pycache__", ignore_errors=True)

    assert result.returncode == 1
    assert "api must not import infrastructure" in result.stderr
