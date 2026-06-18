"""Phase 3D-H1 — Descriptor capability binding integrity / Phase 3C drift.

Hardens Lens 3: every descriptor must bind **only** to existing Phase 3C
Capability Registry capabilityIds. A descriptor can never introduce a new
capabilityId, never bind to a missing / malformed one, and never be marked
visible while binding a forbidden capability. If the Phase 3C index drifts
(a bound capabilityId disappears), descriptor validation must fail closed.

Phase: 3D-H1 — Static Plugin Descriptor Registry Hardening
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from hermes_cli.dev_web_capability_registry_manifest import (
    get_static_manifest as get_capability_manifest,
)
from hermes_cli.dev_web_plugin_descriptor_manifest import get_static_manifest
from hermes_cli.dev_web_plugin_descriptor_policy import (
    build_capability_index,
    check_descriptor_policy,
    inherited_permission_class,
)
from hermes_cli.dev_web_plugin_descriptor_registry import validate_manifest
from hermes_cli.dev_web_plugin_descriptor_schema import is_terminal_forbidden_permission


def _base_entry() -> dict[str, Any]:
    return copy.deepcopy(get_static_manifest()[0])


class TestBindingsExistInPhase3C:
    def test_capability_index_is_non_empty(self) -> None:
        index = build_capability_index()
        assert len(index) > 0

    def test_index_contains_every_phase_3c_capability(self) -> None:
        index = build_capability_index()
        cap_ids = {e["capabilityId"] for e in get_capability_manifest()}
        assert set(index) == cap_ids

    def test_every_descriptor_binds_only_existing_capability_ids(self) -> None:
        index = build_capability_index()
        for entry in get_static_manifest():
            for cid in entry["capabilityBindings"]:
                assert cid in index, f"{entry['pluginId']} binds unknown capability {cid}"

    def test_no_descriptor_introduces_a_new_capability_id(self) -> None:
        index = build_capability_index()
        for entry in get_static_manifest():
            for cid in entry["capabilityBindings"]:
                assert cid in index


class TestInheritedPermission:
    def test_inherited_permission_for_each_descriptor_is_valid(self) -> None:
        index = build_capability_index()
        for entry in get_static_manifest():
            inherited = inherited_permission_class(entry["capabilityBindings"], index)
            assert inherited is not None, entry["pluginId"]
            assert inherited == entry["permissionClass"], entry["pluginId"]

    def test_inherited_returns_none_for_empty_bindings(self) -> None:
        assert inherited_permission_class([], build_capability_index()) is None
        assert inherited_permission_class(()) is None

    def test_inherited_returns_none_for_unknown_capability(self) -> None:
        assert inherited_permission_class(["capability.does.not.exist"]) is None


class TestMissingOrMalformedCapabilityRejected:
    def test_missing_capability_id_rejected(self) -> None:
        entry = _base_entry()
        entry["capabilityBindings"] = ("capability.that.does_not_exist",)
        errors = check_descriptor_policy(entry)
        assert any("does not exist" in e.reason for e in errors)

    def test_malformed_capability_id_rejected(self) -> None:
        entry = _base_entry()
        entry["capabilityBindings"] = ("not-a-valid-id",)
        errors = check_descriptor_policy(entry)
        assert any("invalid capabilityId format" in e.reason for e in errors)

    def test_new_invented_capability_id_rejected(self) -> None:
        entry = _base_entry()
        entry["capabilityBindings"] = ("brand.new.invented.capability",)
        errors = check_descriptor_policy(entry)
        assert any("does not exist" in e.reason for e in errors)

    def test_empty_bindings_rejected(self) -> None:
        entry = _base_entry()
        entry["capabilityBindings"] = ()
        errors = check_descriptor_policy(entry)
        assert any("non-empty list" in e.reason for e in errors)


class TestForbiddenCapabilityBinding:
    def test_binding_forbidden_capability_cannot_be_visible(self) -> None:
        entry = _base_entry()
        # Bind a forbidden capability and force visible + verified trust.
        entry["capabilityBindings"] = ("capability.forbidden.shell",)
        entry["permissionClass"] = "EXTERNAL_FORBIDDEN"
        entry["trustLevel"] = "trusted_static_descriptor"
        entry["status"] = "visible"
        errors = check_descriptor_policy(entry)
        assert any("must be blocked" in e.reason for e in errors)

    def test_binding_forbidden_capability_inherits_terminal(self) -> None:
        index = build_capability_index()
        inherited = inherited_permission_class(("capability.forbidden.shell",), index)
        assert inherited is not None
        assert is_terminal_forbidden_permission(inherited)

    def test_production_forbidden_capability_binding(self) -> None:
        index = build_capability_index()
        inherited = inherited_permission_class(
            ("capability.forbidden.production_operation",), index
        )
        assert inherited == "PRODUCTION_FORBIDDEN"


class TestPhase3CDriftBoundary:
    def test_drift_missing_capability_causes_binding_failure(self) -> None:
        """If a Phase 3C capabilityId disappears, the descriptor must fail."""
        index = build_capability_index()
        # Simulate drift: drop every capabilityId the first descriptor binds to.
        drifted = {
            cid: pc
            for cid, pc in index.items()
            if cid not in get_static_manifest()[0]["capabilityBindings"]
        }
        entry = _base_entry()
        errors = check_descriptor_policy(entry, drifted)
        assert any("does not exist" in e.reason for e in errors)

    def test_drift_empty_index_rejects_all_bindings(self) -> None:
        entry = _base_entry()
        errors = check_descriptor_policy(entry, {})
        assert any("does not exist" in e.reason for e in errors)

    def test_stricter_phase_3c_permission_is_inherited(self) -> None:
        # If the bound capability carries WRITE_CONFIRM, the descriptor may not
        # declare the less-restrictive READ_ONLY (escalation rejected).
        entry = _base_entry()
        entry["capabilityBindings"] = ("tool.sandbox.dev_sandbox_file_write",)  # WRITE_CONFIRM
        entry["permissionClass"] = "READ_ONLY"  # less restrictive → escalation
        errors = check_descriptor_policy(entry)
        assert any("permission escalation" in e.reason for e in errors)

    def test_valid_manifest_passes_with_real_index(self) -> None:
        report = validate_manifest(get_static_manifest())
        assert report.valid
