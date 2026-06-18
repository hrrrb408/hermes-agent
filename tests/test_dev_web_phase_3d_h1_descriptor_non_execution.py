"""Phase 3D-H1 — Non-execution boundary / no runtime / no loader / no execution path.

Hardens Lens 6: the registry module exposes **no** execution surface — no
``execute`` / ``load_plugin`` / ``install_plugin`` / ``enable_plugin`` /
``grant_permission`` / ``create_approval`` / ``create_confirmation_token`` /
``create_dry_run`` / ``create_route`` API. The frozen no-runtime flags hold,
``is_executable_execution_mode`` is always False, and every descriptor stays in
a non-executable ``descriptor_only`` mode.

Phase: 3D-H1 — Static Plugin Descriptor Registry Hardening
"""

from __future__ import annotations

import pytest

from hermes_cli import dev_web_plugin_descriptor_registry as registry_mod
from hermes_cli.dev_web_plugin_descriptor_manifest import get_static_manifest
from hermes_cli.dev_web_plugin_descriptor_registry import (
    NEW_ROUTE_INTRODUCED,
    PLUGIN_EXECUTION_ALLOWED,
    PLUGIN_LOADER_IMPLEMENTED,
    PLUGIN_RUNTIME_IMPLEMENTED,
    assert_no_plugin_runtime,
)
from hermes_cli.dev_web_plugin_descriptor_schema import (
    NON_EXECUTABLE_PLUGIN_STATUSES,
    PLUGIN_EXECUTION_MODES,
    PLUGIN_STATUSES,
    is_executable_execution_mode,
)

_FORBIDDEN_EXECUTION_APIS = (
    "execute",
    "execute_plugin",
    "execute_descriptor",
    "load_plugin",
    "run_plugin",
    "install_plugin",
    "uninstall_plugin",
    "enable_plugin",
    "disable_plugin",
    "reload_plugin",
    "import_plugin",
    "register_plugin",
    "register_descriptor",
    "create_descriptor",
    "create_descriptor_from_provider",
    "create_descriptor_from_tool_calls",
    "grant_permission",
    "approve",
    "create_approval",
    "create_confirmation_token",
    "create_dry_run",
    "create_route",
    "create_execution_path",
    "request_execution",
    "invoke",
    "call_tool",
    "call_provider",
    "advance_workflow",
)


class TestNoExecutionApi:
    @pytest.mark.parametrize("attr", _FORBIDDEN_EXECUTION_APIS)
    def test_registry_module_has_no_execution_api(self, attr: str) -> None:
        assert not hasattr(registry_mod, attr), f"unexpected execution API: {attr}"

    def test_callables_on_module_are_descriptive_only(self) -> None:
        # Every public callable must be read-only / descriptive.
        execution_verbs = {"execute", "load", "install", "run", "invoke", "grant", "approve"}
        for name in dir(registry_mod):
            if name.startswith("_"):
                continue
            lower = name.lower()
            for verb in execution_verbs:
                assert not lower.startswith(verb), f"execution-shaped public name: {name}"


class TestNoRuntimeFlags:
    def test_plugin_runtime_not_implemented(self) -> None:
        assert PLUGIN_RUNTIME_IMPLEMENTED is False

    def test_plugin_loader_not_implemented(self) -> None:
        assert PLUGIN_LOADER_IMPLEMENTED is False

    def test_plugin_execution_not_allowed(self) -> None:
        assert PLUGIN_EXECUTION_ALLOWED is False

    def test_no_new_route_introduced(self) -> None:
        assert NEW_ROUTE_INTRODUCED is False

    def test_assert_no_plugin_runtime_passes(self) -> None:
        # The assertion helper must not raise — flags are frozen.
        assert_no_plugin_runtime()


class TestNoExecutableMode:
    def test_is_executable_execution_mode_always_false(self) -> None:
        for mode in PLUGIN_EXECUTION_MODES:
            assert is_executable_execution_mode(mode) is False
        # Any arbitrary value is also non-executable.
        assert is_executable_execution_mode("installed") is False
        assert is_executable_execution_mode("executing") is False

    def test_no_executable_lifecycle_status_exists(self) -> None:
        # The taxonomy has no installed / loaded / executing status.
        executable_statuses = {"installed", "loaded", "executing", "running", "active"}
        assert PLUGIN_STATUSES.isdisjoint(executable_statuses)
        assert NON_EXECUTABLE_PLUGIN_STATUSES == PLUGIN_STATUSES

    def test_every_descriptor_is_descriptor_only(self) -> None:
        for entry in get_static_manifest():
            assert entry["executionMode"] == "descriptor_only", entry["pluginId"]
            assert entry["executionMode"] in PLUGIN_EXECUTION_MODES

    def test_every_descriptor_status_is_non_executable(self) -> None:
        for entry in get_static_manifest():
            assert entry["status"] in NON_EXECUTABLE_PLUGIN_STATUSES, entry["pluginId"]


class TestNoApprovalOrRouteCreation:
    def test_registry_creates_no_approval_or_route(self) -> None:
        # The status block must not carry an approval / route / execution path.
        from hermes_cli.dev_web_plugin_descriptor_registry import get_plugin_descriptor_status_block

        block = get_plugin_descriptor_status_block()
        for key in ("approvalRequired", "routeCreated", "executionPath", "approvalCreated"):
            assert key not in block
        assert block["pluginExecutionAllowed"] is False
