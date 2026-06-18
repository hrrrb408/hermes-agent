"""Phase 3C-H1 — PermissionClass / TrustLevel / Status Coherence Hardening.

Hardens ``CAP-PERMISSION-TRUST-3C-H1-001`` (Lens 4).

Verifies the frozen composition rules between ``permissionClass``,
``trustLevel``, ``status``, and the runtime gate flags. The registry only
*describes*; these rules confirm no described capability can be inconsistent
(e.g. an enabled forbidden class, a WRITE_CONFIRM without a dry-run gate, a
LIVE_PROVIDER_GATED without a kill switch, a blocked entry without a reason).
Every first-version capability keeps ``devOnly = True`` and
``productionAllowed = False``.

Phase: 3C-H1 — Static Capability Registry Hardening
Status: implemented
"""

from __future__ import annotations

import copy

import pytest

from hermes_cli.dev_web_capability_registry import validate_manifest
from hermes_cli.dev_web_capability_registry_manifest import get_static_manifest


def _base_entry() -> dict:
    """A fully-valid READ_ONLY enabled entry (a known-good baseline)."""
    return {
        "capabilityId": "tool.read.coherence_probe",
        "displayName": "Probe",
        "description": "coherence probe",
        "category": "tool",
        "status": "enabled",
        "permissionClass": "READ_ONLY",
        "trustLevel": "BUILTIN_VERIFIED",
        "executionMode": "read_only",
        "routeExposure": "existing_route_only",
        "requiresApproval": False,
        "requiresDryRun": False,
        "requiresConfirmation": False,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": False,
        "blockedReason": None,
        "auditEventPrefix": "probe_",
        "metadataSchema": "probe_v1",
    }


def _valid_entry(**overrides) -> dict:
    e = _base_entry()
    e.update(overrides)
    return e


def _is_valid(entry: dict) -> bool:
    return validate_manifest([entry]).valid


class TestEnabledRequiresVerifiedTrust:
    def test_enabled_builtin_verified_ok(self) -> None:
        assert _is_valid(_valid_entry(trustLevel="BUILTIN_VERIFIED"))

    def test_enabled_dev_static_manifest_ok(self) -> None:
        assert _is_valid(_valid_entry(trustLevel="DEV_STATIC_MANIFEST"))

    def test_enabled_experimental_disabled_invalid(self) -> None:
        assert not _is_valid(_valid_entry(trustLevel="EXPERIMENTAL_DISABLED"))

    def test_enabled_external_forbidden_invalid(self) -> None:
        assert not _is_valid(_valid_entry(trustLevel="EXTERNAL_FORBIDDEN"))

    def test_enabled_unknown_forbidden_invalid(self) -> None:
        assert not _is_valid(_valid_entry(trustLevel="UNKNOWN_FORBIDDEN"))


class TestForbiddenClassesNonExecutable:
    @pytest.mark.parametrize(
        "permission_class",
        ["ADMIN_FORBIDDEN", "EXTERNAL_FORBIDDEN", "PRODUCTION_FORBIDDEN"],
    )
    def test_forbidden_class_enabled_is_invalid(self, permission_class: str) -> None:
        # Enabled + forbidden class must be rejected.
        entry = _valid_entry(permissionClass=permission_class)
        assert not _is_valid(entry)

    @pytest.mark.parametrize(
        "permission_class,trust_level",
        [
            ("ADMIN_FORBIDDEN", "EXPERIMENTAL_DISABLED"),
            ("EXTERNAL_FORBIDDEN", "EXTERNAL_FORBIDDEN"),
            ("PRODUCTION_FORBIDDEN", "EXTERNAL_FORBIDDEN"),
        ],
    )
    def test_forbidden_class_blocked_ok(self, permission_class: str, trust_level: str) -> None:
        entry = _valid_entry(
            permissionClass=permission_class,
            trustLevel=trust_level,
            status="blocked",
            executionMode="none",
            routeExposure="forbidden_new_route",
            blockedReason="coherence_probe_blocked",
        )
        assert _is_valid(entry), f"blocked {permission_class} should be valid"


class TestGateCoherence:
    def test_write_confirm_requires_dry_run(self) -> None:
        e = _valid_entry(
            permissionClass="WRITE_CONFIRM",
            executionMode="confirmed_execute",
            requiresDryRun=False,
            requiresConfirmation=True,
            requiresAudit=True,
        )
        assert not _is_valid(e)

    def test_write_confirm_requires_confirmation(self) -> None:
        e = _valid_entry(
            permissionClass="WRITE_CONFIRM",
            executionMode="confirmed_execute",
            requiresDryRun=True,
            requiresConfirmation=False,
            requiresAudit=True,
        )
        assert not _is_valid(e)

    def test_write_confirm_requires_audit(self) -> None:
        e = _valid_entry(
            permissionClass="WRITE_CONFIRM",
            executionMode="confirmed_execute",
            requiresDryRun=True,
            requiresConfirmation=True,
            requiresAudit=False,
        )
        assert not _is_valid(e)

    def test_write_confirm_fully_gated_ok(self) -> None:
        e = _valid_entry(
            permissionClass="WRITE_CONFIRM",
            executionMode="confirmed_execute",
            requiresDryRun=True,
            requiresConfirmation=True,
            requiresAudit=True,
        )
        assert _is_valid(e)

    def test_rollback_confirm_requires_confirmation(self) -> None:
        e = _valid_entry(
            permissionClass="ROLLBACK_CONFIRM",
            executionMode="confirmed_execute",
            requiresConfirmation=False,
            requiresAudit=True,
        )
        assert not _is_valid(e)

    def test_rollback_confirm_requires_audit(self) -> None:
        e = _valid_entry(
            permissionClass="ROLLBACK_CONFIRM",
            executionMode="confirmed_execute",
            requiresConfirmation=True,
            requiresAudit=False,
        )
        assert not _is_valid(e)

    def test_live_provider_gated_requires_all_four_gates(self) -> None:
        base = {
            "permissionClass": "LIVE_PROVIDER_GATED",
            "executionMode": "manual_live",
            "requiresApproval": True,
            "requiresBudget": True,
            "requiresKillSwitch": True,
            "requiresAudit": True,
        }
        assert _is_valid(_valid_entry(**base))
        for missing in ("requiresApproval", "requiresBudget", "requiresKillSwitch", "requiresAudit"):
            e = _valid_entry(**{**base, missing: False})
            assert not _is_valid(e), f"LIVE_PROVIDER_GATED missing {missing} should be invalid"

    def test_read_only_cannot_declare_confirmed_execute(self) -> None:
        e = _valid_entry(executionMode="confirmed_execute")
        assert not _is_valid(e)

    def test_read_only_cannot_declare_manual_live(self) -> None:
        e = _valid_entry(executionMode="manual_live")
        assert not _is_valid(e)


class TestBlockedRequiresReason:
    def test_blocked_without_reason_invalid(self) -> None:
        e = _valid_entry(
            permissionClass="ADMIN_FORBIDDEN",
            trustLevel="EXPERIMENTAL_DISABLED",
            status="blocked",
            executionMode="none",
            routeExposure="forbidden_new_route",
            blockedReason=None,
        )
        assert not _is_valid(e)

    def test_blocked_with_reason_ok(self) -> None:
        e = _valid_entry(
            permissionClass="ADMIN_FORBIDDEN",
            trustLevel="EXPERIMENTAL_DISABLED",
            status="blocked",
            executionMode="none",
            routeExposure="forbidden_new_route",
            blockedReason="probe_blocked_reason",
        )
        assert _is_valid(e)


class TestFirstVersionInvariants:
    def test_production_allowed_true_invalid(self) -> None:
        e = _valid_entry(productionAllowed=True)
        assert not _is_valid(e)

    def test_dev_only_false_invalid(self) -> None:
        e = _valid_entry(devOnly=False)
        assert not _is_valid(e)

    def test_static_manifest_all_dev_only_and_not_production(self) -> None:
        for entry in get_static_manifest():
            assert entry["devOnly"] is True, entry["capabilityId"]
            assert entry["productionAllowed"] is False, entry["capabilityId"]

    def test_static_manifest_no_enabled_forbidden_class(self) -> None:
        for entry in get_static_manifest():
            if entry["status"] == "enabled":
                assert entry["permissionClass"] in {
                    "READ_ONLY",
                    "WRITE_PREVIEW",
                    "WRITE_CONFIRM",
                    "ROLLBACK_CONFIRM",
                    "LIVE_PROVIDER_GATED",
                }, entry["capabilityId"]
                assert entry["trustLevel"] in {
                    "BUILTIN_VERIFIED",
                    "DEV_STATIC_MANIFEST",
                }, entry["capabilityId"]

    def test_static_manifest_blocked_entries_have_reason(self) -> None:
        for entry in get_static_manifest():
            if entry["status"] == "blocked":
                assert entry.get("blockedReason"), entry["capabilityId"]

    def test_static_manifest_validates_clean(self) -> None:
        assert validate_manifest(get_static_manifest()).valid is True
