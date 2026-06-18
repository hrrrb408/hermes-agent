"""Phase 3D — Plugin Descriptor trust-classification tests.

Verifies trust / status coherence: visible requires a verified trust level,
forbidden trust levels must be blocked, experimental-disabled must be
disabled/blocked, and trust self-upgrade (a descriptor bound to forbidden
capabilities carrying a verified trust level) is rejected.

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_plugin_descriptor_policy import build_capability_index, check_descriptor_policy
from hermes_cli.dev_web_plugin_descriptor_registry import validate_manifest

_INDEX = build_capability_index()


def _entry(**overrides: object) -> dict:
    base: dict = {
        "pluginId": "plugin.descriptor.trust_test",
        "displayName": "t",
        "source": "tracked_static_descriptor",
        "trustLevel": "dev_reviewed_descriptor",
        "status": "disabled",
        "capabilityBindings": ("registry.capability_registry_detail",),
        "permissionClass": "READ_ONLY",
        "executionMode": "descriptor_only",
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
    }
    base.update(overrides)
    return base


class TestVisibleRequiresVerifiedTrust:
    def test_visible_with_verified_trust_accepted(self) -> None:
        entry = _entry(
            status="visible",
            trustLevel="trusted_static_descriptor",
            source="builtin_static",
        )
        errors = check_descriptor_policy(entry, _INDEX)
        assert errors == []

    def test_visible_with_unverified_trust_rejected(self) -> None:
        entry = _entry(
            status="visible",
            trustLevel="dev_reviewed_descriptor",
        )
        errors = check_descriptor_policy(entry, _INDEX)
        assert any("visible requires a verified trust level" in e.reason for e in errors)


class TestForbiddenTrustMustBeBlocked:
    @pytest.mark.parametrize("trust", ["external_forbidden", "unknown_forbidden", "production_forbidden"])
    def test_forbidden_trust_not_blocked_rejected(self, trust: str) -> None:
        entry = _entry(
            trustLevel=trust,
            source="external_forbidden",
            status="disabled",  # wrong — must be blocked
        )
        errors = check_descriptor_policy(entry, _INDEX)
        assert any("must be blocked" in e.reason for e in errors)

    def test_forbidden_trust_blocked_accepted(self) -> None:
        entry = _entry(
            trustLevel="external_forbidden",
            source="external_forbidden",
            status="blocked",
            blockedReason="x",
            capabilityBindings=("capability.forbidden.marketplace",),
            permissionClass="EXTERNAL_FORBIDDEN",
        )
        errors = check_descriptor_policy(entry, _INDEX)
        assert errors == []


class TestExperimentalDisabled:
    def test_experimental_disabled_visible_rejected(self) -> None:
        entry = _entry(
            trustLevel="experimental_disabled_descriptor",
            status="visible",
        )
        errors = check_descriptor_policy(entry, _INDEX)
        assert any("experimental_disabled_descriptor must be" in e.reason for e in errors)

    def test_experimental_disabled_disabled_accepted(self) -> None:
        entry = _entry(trustLevel="experimental_disabled_descriptor", status="disabled")
        errors = check_descriptor_policy(entry, _INDEX)
        assert errors == []


class TestTrustSelfUpgradeRejected:
    def test_verified_trust_on_forbidden_binding_rejected(self) -> None:
        # A descriptor bound to a forbidden capability may not claim a verified
        # trust level (trust self-upgrade).
        entry = _entry(
            capabilityBindings=("capability.forbidden.marketplace",),
            permissionClass="EXTERNAL_FORBIDDEN",
            trustLevel="trusted_static_descriptor",  # self-upgrade attempt
            source="external_forbidden",
            status="blocked",
            blockedReason="x",
        )
        errors = check_descriptor_policy(entry, _INDEX)
        assert any("verified trust level" in e.reason for e in errors)


class TestStaticManifestTrustCoherence:
    def test_static_manifest_has_no_trust_violations(self) -> None:
        from hermes_cli.dev_web_plugin_descriptor_manifest import get_static_manifest

        report = validate_manifest(get_static_manifest())
        assert report.valid
        # The trust taxonomy is exercised: at least 3 distinct trust levels used.
        assert len(report.trust_level_counts) >= 3
        assert report.trust_level_counts.get("trusted_static_descriptor") == 3
        assert report.trust_level_counts.get("dev_reviewed_descriptor") == 4
