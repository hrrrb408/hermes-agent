"""Phase 3C — Capability Registry validation tests.

Verifies ``validate_manifest`` fails closed on: missing required fields,
invalid enums, duplicate ids, unknown fields, and every forbidden field.
Verifies the static manifest validates clean and the report counts are correct.

Phase: 3C — Static dev-only Capability Registry
"""

from __future__ import annotations

import copy

from hermes_cli.dev_web_capability_registry import validate_manifest
from hermes_cli.dev_web_capability_registry_manifest import get_static_manifest
from hermes_cli.dev_web_capability_registry_schema import FORBIDDEN_FIELDS


def _good_entry(cid: str = "tool.read.example_read") -> dict:
    return {
        "capabilityId": cid,
        "displayName": "Example",
        "description": "example",
        "category": "tool",
        "version": "phase3c-static-v1",
        "owner": "phase-3c",
        "source": "static_manifest",
        "status": "enabled",
        "permissionClass": "READ_ONLY",
        "trustLevel": "BUILTIN_VERIFIED",
        "executionMode": "read_only",
        "routeExposure": "no_route",
        "requiresApproval": False,
        "requiresDryRun": False,
        "requiresConfirmation": False,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": False,
        "auditEventPrefix": "example_",
        "metadataSchema": "example_v1",
        "createdAt": "2026-06-17T00:00:00Z",
        "updatedAt": "2026-06-17T00:00:00Z",
    }


class TestStaticManifestValidates:
    def test_static_manifest_valid(self) -> None:
        report = validate_manifest(get_static_manifest())
        assert report.valid is True
        assert report.error_count == 0
        assert report.capability_count == len(get_static_manifest())

    def test_static_manifest_unique_ids(self) -> None:
        ids = [e["capabilityId"] for e in get_static_manifest()]
        assert len(ids) == len(set(ids))

    def test_report_counts_match(self) -> None:
        report = validate_manifest(get_static_manifest())
        assert sum(report.status_counts.values()) == report.capability_count
        assert sum(report.permission_class_counts.values()) == report.capability_count
        assert sum(report.trust_level_counts.values()) == report.capability_count
        assert sum(report.category_counts.values()) == report.capability_count
        assert report.blocked_count == report.status_counts.get("blocked", 0)


class TestRequiredAndEnumValidation:
    def test_missing_required_field_fails(self) -> None:
        entry = _good_entry()
        del entry["permissionClass"]
        report = validate_manifest([entry])
        assert not report.valid
        assert any(e.field == "permissionClass" for e in report.errors)

    def test_invalid_category_fails(self) -> None:
        entry = _good_entry()
        entry["category"] = "network"
        assert not validate_manifest([entry]).valid

    def test_invalid_status_fails(self) -> None:
        entry = _good_entry()
        entry["status"] = "active"
        assert not validate_manifest([entry]).valid

    def test_invalid_permission_class_fails(self) -> None:
        entry = _good_entry()
        entry["permissionClass"] = "GOD_MODE"
        assert not validate_manifest([entry]).valid

    def test_invalid_trust_level_fails(self) -> None:
        entry = _good_entry()
        entry["trustLevel"] = "REMOTE_TRUSTED"
        assert not validate_manifest([entry]).valid

    def test_invalid_execution_mode_fails(self) -> None:
        entry = _good_entry()
        entry["executionMode"] = "auto"
        assert not validate_manifest([entry]).valid

    def test_invalid_route_exposure_fails(self) -> None:
        entry = _good_entry()
        entry["routeExposure"] = "new_route_ok"
        assert not validate_manifest([entry]).valid

    def test_invalid_source_fails(self) -> None:
        entry = _good_entry()
        entry["source"] = "remote_marketplace"
        assert not validate_manifest([entry]).valid

    def test_bad_capability_id_format_fails(self) -> None:
        entry = _good_entry(cid="bad id")
        report = validate_manifest([entry])
        assert not report.valid
        assert any(e.field == "capabilityId" for e in report.errors)

    def test_non_bool_flag_fails(self) -> None:
        entry = _good_entry()
        entry["requiresAudit"] = "yes"
        assert not validate_manifest([entry]).valid


class TestFirstVersionInvariants:
    def test_dev_only_false_fails(self) -> None:
        entry = _good_entry()
        entry["devOnly"] = False
        assert not validate_manifest([entry]).valid

    def test_production_allowed_true_fails(self) -> None:
        entry = _good_entry()
        entry["productionAllowed"] = True
        assert not validate_manifest([entry]).valid

    def test_blocked_without_reason_fails(self) -> None:
        entry = _good_entry()
        entry["status"] = "blocked"
        entry["permissionClass"] = "ADMIN_FORBIDDEN"
        entry["trustLevel"] = "EXPERIMENTAL_DISABLED"
        entry["executionMode"] = "none"
        entry["routeExposure"] = "forbidden_new_route"
        # no blockedReason
        assert not validate_manifest([entry]).valid


class TestDuplicateAndUnknown:
    def test_duplicate_capability_id_fails(self) -> None:
        a = _good_entry("tool.read.dup")
        b = _good_entry("tool.read.dup")
        report = validate_manifest([a, b])
        assert not report.valid
        assert any("duplicate" in e.reason for e in report.errors)

    def test_unknown_field_fails(self) -> None:
        entry = _good_entry()
        entry["surpriseField"] = "x"
        assert not validate_manifest([entry]).valid


class TestForbiddenFieldsRejected:
    def test_each_forbidden_field_rejected(self) -> None:
        for field_name in FORBIDDEN_FIELDS:
            entry = _good_entry()
            entry[field_name] = "evil-payload"
            report = validate_manifest([entry])
            assert not report.valid, f"forbidden field {field_name} was not rejected"
            assert any(e.field == field_name for e in report.errors), field_name

    def test_forbidden_field_rejects_entry_outright(self) -> None:
        entry = _good_entry()
        entry["pythonImportPath"] = "evil.module"
        report = validate_manifest([entry])
        # The forbidden-field check returns immediately — only one error.
        assert report.error_count == 1
        assert report.errors[0].field == "pythonImportPath"

    def test_validation_not_silently_ignored(self) -> None:
        # A manifest with one clean + one forbidden entry is invalid overall.
        good = _good_entry("tool.read.clean")
        bad = _good_entry("tool.read.bad")
        bad["shellCommand"] = "rm -rf /"
        assert not validate_manifest([good, bad]).valid


class TestDeterminism:
    def test_two_validations_identical(self) -> None:
        r1 = validate_manifest(get_static_manifest())
        r2 = validate_manifest(get_static_manifest())
        assert r1.valid == r2.valid
        assert r1.capability_count == r2.capability_count
        assert r1.permission_class_counts == r2.permission_class_counts
        assert r1.status_counts == r2.status_counts

    def test_copy_independent(self) -> None:
        entries = [copy.deepcopy(_good_entry("tool.read.copy_a"))]
        report = validate_manifest(entries)
        assert report.valid
        # Mutating the input afterwards must not change the prior report shape.
        entries[0]["status"] = "blocked"
        assert report.status_counts.get("enabled") == 1
