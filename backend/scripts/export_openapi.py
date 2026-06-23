from __future__ import annotations

import argparse
import json
from pathlib import Path

from hify.bootstrap.api import create_app


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
DEFAULT_OUTPUT_PATH = (
    REPOSITORY_ROOT / "apps" / "web" / "src" / "lib" / "api" / "generated" / "openapi.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the Hify FastAPI OpenAPI schema.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="OpenAPI JSON output path.",
    )
    args = parser.parse_args()

    output_path = args.output
    if not output_path.is_absolute():
        output_path = (REPOSITORY_ROOT / output_path).resolve()

    app = create_app()
    schema = app.openapi()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
