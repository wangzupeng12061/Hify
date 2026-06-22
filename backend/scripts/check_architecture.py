from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "hify"
MODULES_ROOT = SRC / "modules"

EXPECTED_MODULES = {
    "identity",
    "providers",
    "agents",
    "conversations",
    "runs",
    "knowledge",
    "workflows",
    "tools",
    "mcp",
    "usage",
    "jobs",
}

REQUIRED_LAYERS = {
    "api",
    "application",
    "domain",
    "infrastructure",
    "contracts",
}

ALLOWED_SYNC_DEPENDENCIES = {
    "identity": set(),
    "providers": {"identity"},
    "jobs": {"identity"},
    "mcp": {"identity"},
    "knowledge": {"identity", "providers"},
    "tools": {"identity", "mcp"},
    "workflows": {"identity", "providers", "tools"},
    "agents": {"identity", "providers", "knowledge", "workflows", "tools"},
    "conversations": {"identity", "agents"},
    "runs": {
        "identity",
        "agents",
        "conversations",
        "providers",
        "knowledge",
        "workflows",
        "tools",
    },
    "usage": {"identity"},
}

FRAMEWORK_AND_SDK_IMPORTS = {
    "fastapi",
    "pydantic",
    "sqlalchemy",
    "celery",
    "redis",
    "langgraph",
    "langchain",
    "langchain_core",
    "openai",
    "anthropic",
    "google",
    "google_genai",
    "ollama",
    "boto3",
    "botocore",
    "pgvector",
}

APPLICATION_FORBIDDEN_IMPORTS = {
    "fastapi",
    "sqlalchemy",
    "openai",
    "anthropic",
    "google",
    "google_genai",
    "ollama",
    "langgraph",
    "langchain",
    "langchain_core",
    "redis",
    "boto3",
    "botocore",
    "pgvector",
}

PROVIDER_SDK_IMPORTS = {"openai", "anthropic", "google", "google_genai", "ollama"}
MCP_SDK_IMPORTS = {"mcp"}


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    message: str

    def format(self) -> str:
        rel = self.path.relative_to(ROOT)
        return f"{rel}:{self.line}: {self.message}"


def main() -> int:
    violations: list[Violation] = []
    violations.extend(check_module_shape())
    violations.extend(check_dependency_graph())

    for path in sorted(SRC.rglob("*.py")):
        violations.extend(check_python_file(path))

    if violations:
        for violation in violations:
            print(violation.format(), file=sys.stderr)
        print(f"{len(violations)} architecture violation(s) found.", file=sys.stderr)
        return 1

    print("Architecture checks passed.")
    return 0


def check_module_shape() -> list[Violation]:
    violations: list[Violation] = []
    actual_modules = {
        p.name
        for p in MODULES_ROOT.iterdir()
        if p.is_dir() and p.name != "__pycache__"
    }

    for module in sorted(EXPECTED_MODULES - actual_modules):
        violations.append(Violation(MODULES_ROOT, 1, f"missing module directory: {module}"))

    for module in sorted(actual_modules - EXPECTED_MODULES):
        violations.append(Violation(MODULES_ROOT / module, 1, f"undeclared module: {module}"))

    for module in sorted(EXPECTED_MODULES & actual_modules):
        module_root = MODULES_ROOT / module
        layers = {
            p.name
            for p in module_root.iterdir()
            if p.is_dir() and p.name != "__pycache__"
        }
        for layer in sorted(REQUIRED_LAYERS - layers):
            violations.append(Violation(module_root, 1, f"missing layer: {layer}"))
        if not (module_root / "wiring.py").exists():
            violations.append(Violation(module_root, 1, "missing wiring.py"))

    return violations


def check_dependency_graph() -> list[Violation]:
    violations: list[Violation] = []
    for module in EXPECTED_MODULES:
        if module not in ALLOWED_SYNC_DEPENDENCIES:
            violations.append(Violation(MODULES_ROOT / module, 1, "missing dependency allowlist row"))

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(module: str, path: tuple[str, ...]) -> None:
        if module in visiting:
            cycle = " -> ".join((*path, module))
            violations.append(Violation(MODULES_ROOT / module, 1, f"dependency cycle: {cycle}"))
            return
        if module in visited:
            return
        visiting.add(module)
        for dependency in ALLOWED_SYNC_DEPENDENCIES.get(module, set()):
            visit(dependency, (*path, module))
        visiting.remove(module)
        visited.add(module)

    for module in sorted(EXPECTED_MODULES):
        visit(module, ())

    return violations


def check_python_file(path: Path) -> list[Violation]:
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError as exc:
        return [Violation(path, exc.lineno or 1, exc.msg)]

    context = module_context(path)
    violations: list[Violation] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                violations.extend(check_import(path, node.lineno, alias.name, context))
        elif isinstance(node, ast.ImportFrom):
            imported = resolve_import_from(path, node)
            if imported:
                violations.extend(check_import(path, node.lineno, imported, context))

    return violations


def module_context(path: Path) -> tuple[str | None, str | None, bool, bool]:
    relative = path.relative_to(SRC)
    parts = relative.parts

    if len(parts) >= 3 and parts[0] == "modules":
        return parts[1], parts[2], False, False

    return None, None, parts[0] == "bootstrap", parts[0] == "processes"


def resolve_import_from(path: Path, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module

    relative = path.relative_to(SRC).with_suffix("")
    package_parts = list(relative.parts[:-1])
    if node.level > len(package_parts):
        return node.module

    base_parts = package_parts[: len(package_parts) - node.level + 1]
    if node.module:
        base_parts.extend(node.module.split("."))

    if not base_parts:
        return None
    return "hify." + ".".join(base_parts)


def check_import(
    path: Path,
    line: int,
    imported: str,
    context: tuple[str | None, str | None, bool, bool],
) -> list[Violation]:
    current_module, current_layer, is_bootstrap, is_process = context
    violations: list[Violation] = []
    top_level = imported.split(".", 1)[0]

    if current_layer == "domain":
        business_import = parse_business_import(imported)
        if imported.startswith("hify.bootstrap"):
            violations.append(Violation(path, line, "domain must not import business modules"))
        if business_import is not None:
            target_module, target_layer = business_import
            if target_module != current_module or target_layer != "domain":
                violations.append(Violation(path, line, "domain must not import business modules"))
        if top_level in FRAMEWORK_AND_SDK_IMPORTS:
            violations.append(Violation(path, line, f"domain must not import {top_level}"))

    if current_layer == "api" and f"hify.modules.{current_module}.infrastructure" in imported:
        violations.append(Violation(path, line, "api must not import infrastructure"))

    if current_layer == "application" and top_level in APPLICATION_FORBIDDEN_IMPORTS:
        violations.append(Violation(path, line, f"application must not import {top_level}"))

    if is_process and imported.startswith("hify.modules."):
        parts = imported.split(".")
        if len(parts) >= 4 and parts[3] != "contracts":
            violations.append(Violation(path, line, "processes may import module contracts only"))

    if top_level == "langgraph" and not is_under(
        path, MODULES_ROOT / "runs" / "infrastructure" / "adapters" / "langgraph"
    ):
        violations.append(Violation(path, line, "langgraph imports are restricted to runs langgraph adapter"))

    if top_level in PROVIDER_SDK_IMPORTS and not is_under(
        path, MODULES_ROOT / "providers" / "infrastructure" / "adapters"
    ):
        violations.append(Violation(path, line, f"{top_level} imports are restricted to provider adapters"))

    if top_level in MCP_SDK_IMPORTS and not is_under(path, MODULES_ROOT / "mcp" / "infrastructure"):
        violations.append(Violation(path, line, "mcp SDK imports are restricted to mcp infrastructure"))

    if top_level == "pgvector" and not is_under(path, MODULES_ROOT / "knowledge" / "infrastructure"):
        violations.append(Violation(path, line, "pgvector imports are restricted to knowledge infrastructure"))

    if imported.startswith("hify.modules."):
        violations.extend(check_module_import(path, line, imported, context, is_bootstrap))

    return violations


def parse_business_import(imported: str) -> tuple[str, str | None] | None:
    parts = imported.split(".")
    if len(parts) < 3 or parts[0] != "hify" or parts[1] != "modules":
        return None
    target_module = parts[2]
    target_layer = parts[3] if len(parts) >= 4 else None
    return target_module, target_layer


def check_module_import(
    path: Path,
    line: int,
    imported: str,
    context: tuple[str | None, str | None, bool, bool],
    is_bootstrap: bool,
) -> list[Violation]:
    current_module, current_layer, _, is_process = context
    business_import = parse_business_import(imported)
    if business_import is None:
        return []

    target_module, target_layer = business_import
    violations: list[Violation] = []

    if target_module == current_module:
        return violations

    if target_layer == "wiring" and not is_bootstrap:
        violations.append(Violation(path, line, "only bootstrap may import module wiring"))

    if current_layer == "domain":
        violations.append(Violation(path, line, "domain must not import other business modules"))
        return violations

    if is_bootstrap:
        return violations

    if is_process:
        if target_layer != "contracts":
            violations.append(Violation(path, line, "processes may import module contracts only"))
        return violations

    if target_layer != "contracts":
        violations.append(Violation(path, line, "cross-module imports must target contracts"))
        return violations

    if current_module and target_module not in ALLOWED_SYNC_DEPENDENCIES[current_module]:
        violations.append(
            Violation(
                path,
                line,
                f"{current_module} may not synchronously depend on {target_module}",
            )
        )

    return violations


def is_under(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
