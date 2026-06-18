"""Phase 3D — Plugin Descriptor Registry no-execution tests.

Verifies there is no plugin runtime, no plugin loader, no execution path, no
executable lifecycle status, no descriptor is ever executed, and that an
"execution request" is blocked by construction. The registry describes future
plugin descriptors only.

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_plugin_descriptor_manifest import get_static_manifest
from hermes_cli.dev_web_plugin_descriptor_registry import (
    NEW_ROUTE_INTRODUCED,
    PLUGIN_EXECUTION_ALLOWED,
    PLUGIN_LOADER_IMPLEMENTED,
    PLUGIN_RUNTIME_IMPLEMENTED,
    assert_no_plugin_runtime,
    validate_manifest,
)
from hermes_cli.dev_web_plugin_descriptor_schema import (
    NON_EXECUTABLE_PLUGIN_STATUSES,
    PLUGIN_EXECUTION_MODES,
    PLUGIN_STATUSES,
    is_executable_execution_mode,
)


class TestNoPluginRuntime:
    def test_plugin_runtime_not_implemented(self) -> None:
        assert PLUGIN_RUNTIME_IMPLEMENTED is False

    def test_plugin_loader_not_implemented(self) -> None:
        assert PLUGIN_LOADER_IMPLEMENTED is False

    def test_plugin_execution_not_allowed(self) -> None:
        assert PLUGIN_EXECUTION_ALLOWED is False

    def test_no_new_route_introduced(self) -> None:
        assert NEW_ROUTE_INTRODUCED is False

    def test_assert_no_plugin_runtime_passes(self) -> None:
        assert_no_plugin_runtime()


class TestNoExecutableLifecycle:
    def test_taxonomy_has_no_executable_status(self) -> None:
        # There is intentionally no installed / loaded / executing status.
        forbidden_statuses = {"installed", "loaded", "executing", "running", "enabled_runtime"}
        assert not (forbidden_statuses & PLUGIN_STATUSES)

    def test_every_status_is_non_executable(self) -> None:
        for status in PLUGIN_STATUSES:
            assert status in NON_EXECUTABLE_PLUGIN_STATUSES

    def test_no_execution_mode_is_executable(self) -> None:
        for mode in PLUGIN_EXECUTION_MODES:
            assert is_executable_execution_mode(mode) is False

    @pytest.mark.parametrize("entry", list(get_static_manifest()))
    def test_no_descriptor_in_executable_status(self, entry: dict) -> None:
        assert entry["status"] != "enabled_runtime"
        assert entry["status"] in NON_EXECUTABLE_PLUGIN_STATUSES
        assert entry["executionMode"] == "descriptor_only"


class TestExecutionRequestBlocked:
    def test_executing_a_descriptor_raises_no_runtime(self) -> None:
        # There is no execute() entry point in the registry. Importing the
        # module and calling validate must not produce any execution surface.
        report = validate_manifest(get_static_manifest())
        assert report.valid
        # No function named execute / load_plugin exists on the registry module.
        from hermes_cli import dev_web_plugin_descriptor_registry as mod

        for forbidden_attr in ("execute", "load_plugin", "run_plugin", "install_plugin", "import_plugin"):
            assert not hasattr(mod, forbidden_attr)

    def test_descriptor_never_grants_execution(self) -> None:
        # Even a visible descriptor is descriptor-only and disabled-by-default.
        for entry in get_static_manifest():
            assert entry["disabledByDefault"] is True
            assert entry["executionMode"] == "descriptor_only"
