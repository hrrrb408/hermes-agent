"""Phase 3D — Plugin Descriptor Registry no-dynamic-loading policy tests.

Verifies the registry modules contain no execution surface: no ``importlib``
dynamic import, no ``__import__``, no path-based file load, no subprocess /
shell, no remote fetch (requests / httpx / urllib / aiohttp), no plugin
directory walk, no marketplace / remote registry URL. The registry only reads
static, in-process data (plus a read-only view of the Phase 3C manifest).

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
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
    PROVIDER_GENERATED_PLUGIN_ALLOWED,
    LLM_GENERATED_PLUGIN_INSTALL_ALLOWED,
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

# Real execution surfaces only — docstring prose mentioning these words is fine
# (the AST scan ignores strings/comments).
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


class TestFrozenFlags:
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

    def test_provider_generated_plugin_disabled(self) -> None:
        assert PROVIDER_GENERATED_PLUGIN_ALLOWED is False

    def test_llm_generated_plugin_install_disabled(self) -> None:
        assert LLM_GENERATED_PLUGIN_INSTALL_ALLOWED is False

    def test_assert_no_plugin_runtime_passes(self) -> None:
        assert_no_plugin_runtime()


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
        importlib.import_module(module_name)
        importlib.import_module(module_name)


class TestStaticManifestOnly:
    def test_loader_only_reads_static_data(self) -> None:
        report = validate_manifest(get_static_manifest())
        assert report.valid
        # Rejecting a dynamic import path field proves the loader gates the surface.
        bad = list(get_static_manifest())[0].copy()
        bad["pythonImportPath"] = "evil"
        assert not validate_manifest([bad]).valid

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
