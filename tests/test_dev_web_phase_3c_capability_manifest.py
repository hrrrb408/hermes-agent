"""Phase 3C — Capability Registry static Manifest tests.

Verifies the static manifest is deterministic, carries no forbidden field,
every entry has devOnly=True / productionAllowed=False, the required
capability ids are present, and the manifest module performs no side effects
(no dynamic import surface).

Phase: 3C — Static dev-only Capability Registry
"""

from __future__ import annotations

import importlib
import inspect

from hermes_cli.dev_web_capability_registry_manifest import (
    CREATED_AT,
    MANIFEST_VERSION,
    STATIC_CAPABILITY_MANIFEST,
    UPDATED_AT,
    get_static_manifest,
)
from hermes_cli.dev_web_capability_registry_schema import FORBIDDEN_FIELDS


class TestManifestShape:
    def test_manifest_is_tuple_of_dicts(self) -> None:
        assert isinstance(STATIC_CAPABILITY_MANIFEST, tuple)
        assert len(STATIC_CAPABILITY_MANIFEST) > 0
        for entry in STATIC_CAPABILITY_MANIFEST:
            assert isinstance(entry, dict)

    def test_get_static_manifest_returns_same_object(self) -> None:
        # Deterministic: returns the same frozen tuple reference.
        assert get_static_manifest() is STATIC_CAPABILITY_MANIFEST

    def test_manifest_version_pinned(self) -> None:
        assert MANIFEST_VERSION == "phase3c-static-v1"

    def test_timestamps_pinned_not_wall_clock(self) -> None:
        assert CREATED_AT == "2026-06-17T00:00:00Z"
        assert UPDATED_AT == "2026-06-17T00:00:00Z"


class TestManifestSafety:
    def test_no_entry_carries_forbidden_field(self) -> None:
        for entry in STATIC_CAPABILITY_MANIFEST:
            for key in entry:
                assert key not in FORBIDDEN_FIELDS, (
                    f"forbidden field {key} in {entry.get('capabilityId')}"
                )

    def test_every_entry_dev_only(self) -> None:
        for entry in STATIC_CAPABILITY_MANIFEST:
            assert entry["devOnly"] is True, entry["capabilityId"]

    def test_every_entry_production_not_allowed(self) -> None:
        for entry in STATIC_CAPABILITY_MANIFEST:
            assert entry["productionAllowed"] is False, entry["capabilityId"]

    def test_blocked_entries_have_reason(self) -> None:
        for entry in STATIC_CAPABILITY_MANIFEST:
            if entry["status"] == "blocked":
                assert entry.get("blockedReason"), entry["capabilityId"]


class TestRequiredCapabilities:
    def _ids(self) -> set[str]:
        return {e["capabilityId"] for e in STATIC_CAPABILITY_MANIFEST}

    def test_registry_capabilities_present(self) -> None:
        ids = self._ids()
        for cid in (
            "registry.capability_registry_status",
            "registry.capability_registry_list",
            "registry.capability_registry_detail",
            "registry.capability_registry_audit",
        ):
            assert cid in ids

    def test_read_only_tool_capabilities_present(self) -> None:
        ids = self._ids()
        for cid in (
            "tool.read.clarify",
            "tool.read.tool_policy_read",
            "tool.read.route_governance_read",
            "tool.read.audit_events_read",
            "tool.read.dev_environment_read",
            "tool.read.release_status_read",
        ):
            assert cid in ids

    def test_sandbox_capabilities_present(self) -> None:
        ids = self._ids()
        for cid in (
            "tool.sandbox.dev_sandbox_file_write",
            "tool.sandbox.dev_sandbox_file_append",
            "tool.sandbox.dev_sandbox_file_patch",
            "tool.sandbox.dev_sandbox_file_readback",
            "tool.sandbox.dev_sandbox_rollback_execute",
        ):
            assert cid in ids

    def test_provider_capabilities_present(self) -> None:
        ids = self._ids()
        for cid in (
            "provider.fake_roundtrip",
            "provider.real_boundary_status",
            "provider.real_request_preview",
            "provider.real_gated_roundtrip",
            "provider.live_manual_one_shot",
            "provider.tool_call_classification",
            "provider.tool_execution",
            "provider.write",
            "provider.auto_write",
            "provider.autonomous_action",
        ):
            assert cid in ids

    def test_workflow_capabilities_present(self) -> None:
        ids = self._ids()
        for cid in (
            "workflow.step.read_only_tool",
            "workflow.step.fake_provider_roundtrip",
            "workflow.step.sandbox_write_preview",
            "workflow.step.rollback_reference",
            "workflow.step.manual_note",
            "workflow.step.audit_query",
            "workflow.write_execute",
            "workflow.rollback_execute",
            "workflow.auto_advance",
            "workflow.autonomous_write",
            "workflow.background_schedule",
        ):
            assert cid in ids

    def test_forbidden_capabilities_present_and_blocked(self) -> None:
        ids = self._ids()
        for cid in (
            "capability.forbidden.dynamic_plugin_load",
            "capability.forbidden.remote_registry",
            "capability.forbidden.marketplace",
            "capability.forbidden.shell",
            "capability.forbidden.database_mutation",
            "capability.forbidden.external_http",
            "capability.forbidden.production_operation",
            "capability.forbidden.provider_write",
            "capability.forbidden.provider_auto_write",
            "capability.forbidden.autonomous_write",
        ):
            assert cid in ids
            entry = next(e for e in STATIC_CAPABILITY_MANIFEST if e["capabilityId"] == cid)
            assert entry["status"] == "blocked", cid


class TestProviderMapping:
    def test_fake_and_boundary_are_read_only(self) -> None:
        by = {e["capabilityId"]: e for e in STATIC_CAPABILITY_MANIFEST}
        assert by["provider.fake_roundtrip"]["permissionClass"] == "READ_ONLY"
        assert by["provider.real_boundary_status"]["permissionClass"] == "READ_ONLY"
        assert by["provider.real_request_preview"]["permissionClass"] == "READ_ONLY"
        assert by["provider.tool_call_classification"]["permissionClass"] == "READ_ONLY"

    def test_live_gated_are_live_provider_gated_and_disabled(self) -> None:
        by = {e["capabilityId"]: e for e in STATIC_CAPABILITY_MANIFEST}
        for cid in ("provider.real_gated_roundtrip", "provider.live_manual_one_shot"):
            assert by[cid]["permissionClass"] == "LIVE_PROVIDER_GATED", cid
            assert by[cid]["status"] == "disabled", cid
            assert by[cid]["executionMode"] == "manual_live", cid

    def test_provider_write_classes_forbidden(self) -> None:
        by = {e["capabilityId"]: e for e in STATIC_CAPABILITY_MANIFEST}
        for cid in ("provider.write", "provider.auto_write", "provider.autonomous_action"):
            assert by[cid]["permissionClass"] == "ADMIN_FORBIDDEN", cid
            assert by[cid]["status"] == "blocked", cid


class TestNoDynamicLoadingSurface:
    def test_module_source_has_no_importlib_or_subprocess(self) -> None:
        import ast
        mod = importlib.import_module("hermes_cli.dev_web_capability_registry_manifest")
        src_path = __import__("pathlib").Path(inspect.getsourcefile(mod))  # type: ignore[arg-type]
        tree = ast.parse(src_path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
        # The manifest is pure data; no execution surface may be imported.
        assert "importlib" not in imports
        assert "subprocess" not in imports
        assert "socket" not in imports
        assert "ctypes" not in imports

    def test_module_source_has_no_remote_fetch(self) -> None:
        import ast
        mod = importlib.import_module("hermes_cli.dev_web_capability_registry_manifest")
        src_path = __import__("pathlib").Path(inspect.getsourcefile(mod))  # type: ignore[arg-type]
        tree = ast.parse(src_path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
        for forbidden in ("requests", "httpx", "urllib", "aiohttp", "http"):
            assert forbidden not in imports, f"manifest module must not import {forbidden!r}"
