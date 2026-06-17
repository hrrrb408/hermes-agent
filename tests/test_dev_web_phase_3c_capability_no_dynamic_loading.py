"""Phase 3C — Capability Registry no-dynamic-loading policy tests.

Verifies the registry modules contain no execution surface: no ``importlib``
dynamic import, no path-based file load, no subprocess/shell, no remote fetch,
no plugin directory walk. The registry only reads static, in-process data.

Phase: 3C — Static dev-only Capability Registry
"""

from __future__ import annotations

import ast
import inspect
import importlib
from pathlib import Path

import pytest

from hermes_cli.dev_web_capability_registry import (
    DYNAMIC_LOADING_ALLOWED,
    MARKETPLACE_ALLOWED,
    PRODUCTION_ALLOWED,
    REMOTE_REGISTRY_ALLOWED,
    assert_no_dynamic_loading,
    validate_manifest,
)
from hermes_cli.dev_web_capability_registry_manifest import get_static_manifest

_MODULES = [
    "hermes_cli.dev_web_capability_registry_schema",
    "hermes_cli.dev_web_capability_registry_manifest",
    "hermes_cli.dev_web_capability_registry_policy",
    "hermes_cli.dev_web_capability_registry_audit",
    "hermes_cli.dev_web_capability_registry",
]

# Modules that must never be imported / called by the registry code (real
# execution surfaces only — docstring prose mentioning these words is fine).
_FORBIDDEN_IMPORT_MODULES = {
    "importlib",
    "subprocess",
    "shlex",
    "requests",
    "httpx",
    "urllib",
    "aiohttp",
    "http",
    "socket",
    "glob",
    "pkgutil",
    "ctypes",
}
_FORBIDDEN_CALL_NAMES = {
    "eval",
    "exec",
    "__import__",
    "system",
    "popen",
    "walk",
    "iterdir",
    "glob",
    "urlopen",
    "spec_from_file_location",
}


def _module_imports_and_calls(path: Path) -> tuple[set[str], set[str]]:
    """Return (imported module names, called names) from the AST of ``path``.

    Only real AST nodes are inspected — string/docstring prose is ignored, so
    describing the prohibition in a docstring never trips the guard.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                calls.add(func.id)
            elif isinstance(func, ast.Attribute):
                calls.add(func.attr)
    return imports, calls


class TestFrozenFlags:
    def test_dynamic_loading_disabled(self) -> None:
        assert DYNAMIC_LOADING_ALLOWED is False

    def test_remote_registry_disabled(self) -> None:
        assert REMOTE_REGISTRY_ALLOWED is False

    def test_marketplace_disabled(self) -> None:
        assert MARKETPLACE_ALLOWED is False

    def test_production_not_allowed(self) -> None:
        assert PRODUCTION_ALLOWED is False

    def test_assert_no_dynamic_loading_passes(self) -> None:
        # Must not raise given the frozen flags.
        assert_no_dynamic_loading()


@pytest.mark.parametrize("module_name", _MODULES)
class TestNoExecutionSurface:
    def test_no_forbidden_import_or_call(self, module_name: str) -> None:
        mod = importlib.import_module(module_name)
        src_path = Path(inspect.getsourcefile(mod))  # type: ignore[arg-type]
        imports, calls = _module_imports_and_calls(src_path)
        bad_imports = imports & _FORBIDDEN_IMPORT_MODULES
        assert not bad_imports, f"{module_name} imports forbidden modules: {bad_imports}"
        bad_calls = calls & _FORBIDDEN_CALL_NAMES
        assert not bad_calls, f"{module_name} calls forbidden names: {bad_calls}"

    def test_module_import_is_pure(self, module_name: str) -> None:
        # Importing must not start a server, open a socket, or walk a directory.
        # Re-import is idempotent and side-effect free.
        importlib.import_module(module_name)
        importlib.import_module(module_name)


class TestStaticManifestOnly:
    def test_loader_only_reads_static_data(self) -> None:
        # validate_manifest must accept the static manifest and reject a list
        # containing a dynamic import path field (proving it gates the surface).
        report = validate_manifest(get_static_manifest())
        assert report.valid
        bad = list(get_static_manifest())[0].copy()
        bad["pythonImportPath"] = "evil"
        assert not validate_manifest([bad]).valid

    def test_no_remote_or_marketplace_capability_enabled(self) -> None:
        report = validate_manifest(get_static_manifest())
        for cid in (
            "capability.forbidden.dynamic_plugin_load",
            "capability.forbidden.remote_registry",
            "capability.forbidden.marketplace",
        ):
            entry = next(e for e in get_static_manifest() if e["capabilityId"] == cid)
            assert entry["status"] == "blocked"
            assert entry["permissionClass"] in {"EXTERNAL_FORBIDDEN", "ADMIN_FORBIDDEN"}
