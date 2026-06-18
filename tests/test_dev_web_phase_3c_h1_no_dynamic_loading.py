"""Phase 3C-H1 — No Dynamic Loading / No Remote Registry / No Marketplace Hardening.

Hardens ``CAP-NO-DYNAMIC-3C-H1-001`` (Lens 8).

The registry is a static, descriptive, in-process manifest. There is no plugin
runtime, no dynamic loading (no ``importlib`` / ``__import__`` / path-based
load / ``pkgutil`` walk), no remote registry fetch, no marketplace, no external
plugin fetch, no provider-generated plugin, and no LLM-generated tool install.

This test AST-walks every registry module and asserts:
  - no import of a dynamic-load / network / shell library,
  - no call to ``eval`` / ``exec`` / ``__import__`` / ``importlib.import_module``
    / ``subprocess.*`` / ``os.system`` / ``shell=True``,
  - the frozen no-dynamic flags hold,
  - the manual one-shot live profile is listed but disabled (never executed).

Phase: 3C-H1 — Static Capability Registry Hardening
Status: implemented
"""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

import pytest

from hermes_cli.dev_web_capability_registry import (
    DYNAMIC_LOADING_ALLOWED,
    DEV_ONLY,
    MARKETPLACE_ALLOWED,
    PRODUCTION_ALLOWED,
    REMOTE_REGISTRY_ALLOWED,
    assert_no_dynamic_loading,
    get_capability_detail,
)
from hermes_cli.dev_web_capability_registry_manifest import get_static_manifest

REGISTRY_MODULES = (
    "hermes_cli.dev_web_capability_registry",
    "hermes_cli.dev_web_capability_registry_manifest",
    "hermes_cli.dev_web_capability_registry_schema",
    "hermes_cli.dev_web_capability_registry_policy",
    "hermes_cli.dev_web_capability_registry_audit",
)

#: Libraries whose import would enable dynamic loading / network / shell.
_FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "importlib",
        "importlib_metadata",
        "pkgutil",
        "ctypes",
        "subprocess",
        "shlex",
        "requests",
        "httpx",
        "urllib",
        "aiohttp",
        "socket",
        "http",
    }
)

#: Bare-name calls that constitute dynamic code execution.
_FORBIDDEN_NAME_CALLS = frozenset({"eval", "exec", "__import__", "compile"})

#: (module_name, attribute) calls that constitute dynamic load / shell / network.
_FORBIDDEN_ATTR_CALLS = frozenset(
    {
        ("importlib", "import_module"),
        ("subprocess", "run"),
        ("subprocess", "Popen"),
        ("subprocess", "call"),
        ("subprocess", "check_call"),
        ("subprocess", "check_output"),
        ("os", "system"),
        ("os", "popen"),
    }
)


def _module_tree(module_name: str) -> tuple[ast.Module, str]:
    mod = importlib.import_module(module_name)
    src_path = Path(inspect.getsourcefile(mod))  # type: ignore[arg-type]
    return ast.parse(src_path.read_text(encoding="utf-8")), src_path.read_text(encoding="utf-8")


class TestNoDynamicLoadImports:
    @pytest.mark.parametrize("module_name", REGISTRY_MODULES)
    def test_no_forbidden_import(self, module_name: str) -> None:
        tree, _ = _module_tree(module_name)
        roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    roots.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    roots.add(node.module.split(".")[0])
        for root in _FORBIDDEN_IMPORT_ROOTS:
            assert root not in roots, f"{module_name} imports forbidden lib: {root}"


class TestNoDynamicExecutionCalls:
    @pytest.mark.parametrize("module_name", REGISTRY_MODULES)
    def test_no_eval_exec_or_dynamic_import_call(self, module_name: str) -> None:
        tree, _ = _module_tree(module_name)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id in _FORBIDDEN_NAME_CALLS:
                pytest.fail(f"{module_name} calls dynamic-exec builtin: {func.id}")
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                key = (func.value.id, func.attr)
                assert key not in _FORBIDDEN_ATTR_CALLS, (
                    f"{module_name} calls forbidden attr: {key}"
                )

    @pytest.mark.parametrize("module_name", REGISTRY_MODULES)
    def test_no_shell_true_keyword(self, module_name: str) -> None:
        tree, _ = _module_tree(module_name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        pytest.fail(f"{module_name} uses shell=True")

    @pytest.mark.parametrize("module_name", REGISTRY_MODULES)
    def test_no_path_based_python_file_load(self, module_name: str) -> None:
        # No exec(open(...)) / load_module / SourceFileLoader patterns.
        _, src = _module_tree(module_name)
        for needle in ("SourceFileLoader", "load_module", "exec_module", "spec_from_file_location"):
            assert needle not in src, f"{module_name} references path-based loader: {needle}"


class TestFrozenNoDynamicFlags:
    def test_flags_are_false_or_true_as_frozen(self) -> None:
        assert DYNAMIC_LOADING_ALLOWED is False
        assert REMOTE_REGISTRY_ALLOWED is False
        assert MARKETPLACE_ALLOWED is False
        assert PRODUCTION_ALLOWED is False
        assert DEV_ONLY is True

    def test_assert_no_dynamic_loading_passes(self) -> None:
        # Does not raise.
        assert_no_dynamic_loading()


class TestManualOneShotListedNotExecuted:
    def test_live_manual_one_shot_listed_disabled(self) -> None:
        d = get_capability_detail(get_static_manifest(), "provider.live_manual_one_shot")
        assert d is not None
        assert d["status"] == "disabled"
        assert d["disabledByDefault"] is True
        assert d["permissionClass"] == "LIVE_PROVIDER_GATED"

    def test_no_capability_enables_live_execution_by_default(self) -> None:
        # No LIVE_PROVIDER_GATED capability is enabled by default.
        for entry in get_static_manifest():
            if entry["permissionClass"] == "LIVE_PROVIDER_GATED":
                assert entry["status"] != "enabled", entry["capabilityId"]
                assert entry["disabledByDefault"] is True, entry["capabilityId"]


class TestForbiddenCapabilitiesDescribedBlocked:
    @pytest.mark.parametrize(
        "cid,fragment",
        [
            ("capability.forbidden.dynamic_plugin_load", "dynamic_plugin_load_forbidden"),
            ("capability.forbidden.remote_registry", "remote_registry_forbidden"),
            ("capability.forbidden.marketplace", "marketplace_forbidden"),
            ("capability.forbidden.shell", "shell_command_forbidden"),
            ("capability.forbidden.database_mutation", "database_mutation_forbidden"),
            ("capability.forbidden.external_http", "external_http_forbidden"),
            ("capability.forbidden.production_operation", "production_operation_forbidden"),
        ],
    )
    def test_forbidden_capability_is_blocked_not_loadable(self, cid: str, fragment: str) -> None:
        d = get_capability_detail(get_static_manifest(), cid)
        assert d is not None
        assert d["status"] == "blocked"
        assert d["executionMode"] == "none"
        # The blocked reason names the forbidden class — describing it, not enabling it.
        assert fragment in (d.get("blockedReason") or "")
