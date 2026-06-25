"""Phase 4B — Target B permission / capability model tests.

Asserts ``hermes_cli/dev_web_target_b_permissions.py`` is frozen and
fail-closed:

  - the 15-permission model denies every permission by default (and none is
    grantable);
  - dangerous permissions (filesystem.write, network.*, secrets.read,
    provider.write, tool.invoke, database.write, process.spawn,
    runtime.execute, plugin.install, marketplace.fetch) are denied
    unconditionally;
  - the capability model is metadata only — every capability is non-executable;
  - untrusted metadata cannot grant a permission;
  - the module source contains NO filesystem / network / subprocess /
    dynamic-import / eval / exec primitive, and no production home or production
    ``state.db`` access.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_permissions as perms
from hermes_cli.dev_web_target_b_permissions import (
    CAPABILITY_KEYS,
    PERMISSION_KEYS,
    assert_permission_layer_disabled,
    build_permission_matrix,
    build_permission_model_report,
    deny_disallowed_permissions,
    evaluate_capability_declaration,
    evaluate_permission_request,
)

DANGEROUS_PERMISSIONS = (
    "filesystem.write",
    "network.http",
    "network.registry",
    "secrets.read",
    "provider.write",
    "tool.invoke",
    "database.write",
    "process.spawn",
    "runtime.execute",
    "plugin.install",
    "marketplace.fetch",
)

FORGED_METADATA_PAYLOADS = [
    {"grant": "true"},
    {"force_allow": "true"},
    {"override": "true"},
    {"approved": "true"},
    {"target_b_authorized": "true"},
]


class TestPermissionModel:
    def test_fifteen_permissions_all_denied_by_default(self) -> None:
        matrix = build_permission_matrix()
        assert len(matrix) == 15
        for entry in matrix:
            assert entry.current_status == "DENIED_BY_DEFAULT"
            assert entry.grantable is False

    def test_taxonomy_covers_all_required_permissions(self) -> None:
        keys = set(PERMISSION_KEYS)
        for required in (
            "filesystem.read",
            "filesystem.write",
            "network.http",
            "network.registry",
            "secrets.read",
            "provider.read",
            "provider.write",
            "ui.render",
            "tool.invoke",
            "database.read",
            "database.write",
            "process.spawn",
            "runtime.execute",
            "plugin.install",
            "marketplace.fetch",
        ):
            assert required in keys

    def test_required_taxonomies_present(self) -> None:
        assert len(PERMISSION_KEYS) == 15
        assert len(CAPABILITY_KEYS) == 6


class TestPermissionEvaluation:
    @pytest.mark.parametrize("permission", PERMISSION_KEYS)
    def test_every_permission_denied(self, permission: str) -> None:
        decision = evaluate_permission_request(permission)
        assert decision.granted is False
        assert decision.current_status == "DENIED_BY_DEFAULT"

    @pytest.mark.parametrize("permission", DANGEROUS_PERMISSIONS)
    def test_dangerous_permission_denied_with_reason(self, permission: str) -> None:
        decision = evaluate_permission_request(permission)
        assert decision.granted is False
        assert decision.reason == "dangerous_permission_denied"

    def test_unknown_permission_denied(self) -> None:
        decision = evaluate_permission_request("shell.execute")
        assert decision.granted is False
        assert decision.reason == "permission_unknown"

    def test_display_only_capability_not_executable(self) -> None:
        decision = evaluate_permission_request("ui.render")
        assert decision.granted is False
        assert decision.reason == "display_only_capability_not_executable"

    def test_tool_invoke_fixture_mode_still_not_granted(self) -> None:
        decision = evaluate_permission_request("tool.invoke", dev_fixture_mode=True)
        assert decision.granted is False

    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_forged_metadata_cannot_grant(self, payload: dict) -> None:
        decision = evaluate_permission_request("runtime.execute", payload)
        assert decision.granted is False

    def test_deny_disallowed_permissions_flags_dangerous(self) -> None:
        disallowed = deny_disallowed_permissions(["filesystem.read", "process.spawn", "shell.execute"])
        assert "process.spawn" in disallowed
        assert "shell.execute" in disallowed
        # read permission is not "disallowed" (it is in taxonomy, not dangerous)
        assert "filesystem.read" not in disallowed


class TestCapabilityModel:
    @pytest.mark.parametrize("capability", CAPABILITY_KEYS)
    def test_every_capability_non_executable(self, capability: str) -> None:
        decision = evaluate_capability_declaration(capability)
        assert decision.recognized is True
        assert decision.executable is False
        assert decision.granted is False

    def test_unknown_capability_rejected(self) -> None:
        decision = evaluate_capability_declaration("execute.code")
        assert decision.recognized is False
        assert decision.executable is False


class TestReportAndBoundary:
    def test_report_any_granted_false(self) -> None:
        report = build_permission_model_report()
        assert report.any_granted is False
        assert report.dangerous_permissions_denied is True
        assert report.permission_count == 15
        assert report.capability_count == 6

    def test_assert_permission_layer_disabled_passes(self) -> None:
        assert_permission_layer_disabled()


class TestSourcePurity:
    MODULE_PATH = Path(perms.__file__)

    FORBIDDEN_USAGE_PATTERNS = (
        "import subprocess",
        "subprocess.",
        "import importlib",
        "importlib.",
        "__import__",
        "import socket",
        "socket.",
        "requests.",
        "httpx.",
        "aiohttp.",
        "urllib",
        "eval(",
        "exec(",
        "os.system",
        "os.popen",
        "Path(",
        "Path.home",
        ".resolve(",
        "open(",
        "read_text(",
        "write_text(",
        "shutil.",
    )

    FORBIDDEN_PATH_STEMS = (
        "~/.hermes",
        ".hermes/state.db",
        "production/state.db",
        "state.db",
    )

    def test_module_source_contains_no_forbidden_usage_primitive(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8")
        for pattern in self.FORBIDDEN_USAGE_PATTERNS:
            assert pattern not in source, f"permissions source must not use {pattern!r}"

    def test_module_source_does_not_reference_production_home_or_state_db(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8").lower()
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, f"permissions source must not reference {stem!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
