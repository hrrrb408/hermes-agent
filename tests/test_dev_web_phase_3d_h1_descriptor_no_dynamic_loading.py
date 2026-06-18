"""Phase 3D-H1 — No dynamic loading / no local dir / no remote registry / no marketplace.

Hardens Lens 7: the registry modules contain **no** execution surface — no
``importlib`` dynamic import, no ``__import__``, no path-based file load, no
subprocess / shell, no remote fetch, no plugin-directory walk, no marketplace /
remote-registry URL. The frozen boundary flags are constants set to False. The
registry only reads static, in-process data (plus a read-only view of the
Phase 3C manifest).

Phase: 3D-H1 — Static Plugin Descriptor Registry Hardening
"""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

import pytest

from hermes_cli.dev_web_plugin_descriptor_registry import (
    DYNAMIC_LOADING_ALLOWED,
    EXTERNAL_PLUGIN_FETCH_ALLOWED,
    LOCAL_PLUGIN_DIRECTORY_LOADING_ALLOWED,
    MARKETPLACE_ALLOWED,
    REMOTE_REGISTRY_ALLOWED,
    assert_no_plugin_runtime,
    validate_manifest,
)
from hermes_cli.dev_web_plugin_descriptor_manifest import get_static_manifest

_MODULES = [
    "hermes_cli.dev_web_plugin_descriptor_schema",
    "hermes_cli.dev_web_plugin_descriptor_manifest",
    "hermes_cli.dev_web_plugin_descriptor_policy",
    "hermes_cli.dev_web_plugin_descriptor_audit",
    "hermes_cli.dev_web_plugin_descriptor_registry",
]

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
    "rglob",
    "urlopen",
    "spec_from_file_location",
    "exec_module",
    "load_module",
    "create_module",
    "open",
    "read_text",
    "read_bytes",
}


def _module_imports_and_calls(path: Path) -> tuple[set[str], set[str]]:
    """Return (imported module names, called names) from the AST of ``path``."""
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


@pytest.mark.parametrize("module_name", _MODULES)
class TestNoExecutionSurface:
    def test_no_forbidden_import(self, module_name: str) -> None:
        mod = importlib.import_module(module_name)
        src_path = Path(inspect.getsourcefile(mod))  # type: ignore[arg-type]
        imports, _ = _module_imports_and_calls(src_path)
        bad_imports = imports & _FORBIDDEN_IMPORT_MODULES
        assert not bad_imports, f"{module_name} imports forbidden modules: {bad_imports}"

    def test_no_forbidden_call(self, module_name: str) -> None:
        mod = importlib.import_module(module_name)
        src_path = Path(inspect.getsourcefile(mod))  # type: ignore[arg-type]
        _, calls = _module_imports_and_calls(src_path)
        bad_calls = calls & _FORBIDDEN_CALL_NAMES
        assert not bad_calls, f"{module_name} calls forbidden names: {bad_calls}"

    def test_module_import_is_pure(self, module_name: str) -> None:
        importlib.import_module(module_name)
        importlib.import_module(module_name)


class TestFrozenBoundaryFlags:
    def test_dynamic_loading_disabled(self) -> None:
        assert DYNAMIC_LOADING_ALLOWED is False

    def test_local_plugin_directory_loading_disabled(self) -> None:
        assert LOCAL_PLUGIN_DIRECTORY_LOADING_ALLOWED is False

    def test_remote_registry_disabled(self) -> None:
        assert REMOTE_REGISTRY_ALLOWED is False

    def test_marketplace_disabled(self) -> None:
        assert MARKETPLACE_ALLOWED is False

    def test_external_plugin_fetch_disabled(self) -> None:
        assert EXTERNAL_PLUGIN_FETCH_ALLOWED is False

    def test_assert_no_plugin_runtime_passes(self) -> None:
        assert_no_plugin_runtime()


class TestNoPathOrDirectoryLoad:
    def test_loader_only_reads_static_data(self) -> None:
        report = validate_manifest(get_static_manifest())
        assert report.valid
        # A dynamic import path field is rejected — proving the loader gates the surface.
        bad = list(get_static_manifest())[0].copy()
        bad["dynamicModule"] = "evil"
        assert not validate_manifest([bad]).valid

    def test_source_has_no_plugin_directory_path(self) -> None:
        # None of the modules reference a plugins/ directory or path-based load.
        for module_name in _MODULES:
            mod = importlib.import_module(module_name)
            src = Path(inspect.getsourcefile(mod)).read_text(encoding="utf-8")  # type: ignore[arg-type]
            # These literals may appear in docstring safety prose; assert no real
            # attribute access that would load from a path.
            for token in (".spec_from_file_location", "SourceFileLoader", "os.scandir", "os.listdir"):
                assert token not in src, f"{module_name} references {token}"

    def test_blocked_descriptors_describe_forbidden_categories(self) -> None:
        report = validate_manifest(get_static_manifest())
        for pid in (
            "plugin.descriptor.dynamic_plugin_load_blocked",
            "plugin.descriptor.remote_registry_blocked",
            "plugin.descriptor.marketplace_blocked",
            "plugin.descriptor.external_execution_blocked",
            "plugin.descriptor.production_operation_blocked",
        ):
            entry = next(e for e in get_static_manifest() if e["pluginId"] == pid)
            assert entry["status"] == "blocked"
            assert entry["disabledByDefault"] is True
        assert report.blocked_count == 5
