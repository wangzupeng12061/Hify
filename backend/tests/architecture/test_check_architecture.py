from __future__ import annotations

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
