"""Phase 3D-H1 — Trust boundary / no self-upgrade / disabled-by-default.

Hardens Lens 5: the trust taxonomy is frozen, forbidden trust levels are always
blocked, ``visible`` requires a verified trust level, and trust self-upgrade is
rejected (a descriptor binding a forbidden capability may never carry a verified
trust level). Every descriptor remains ``devOnly`` / ``productionAllowed=False``
/ ``disabledByDefault=True``.

Phase: 3D-H1 — Static Plugin Descriptor Registry Hardening
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from hermes_cli.dev_web_plugin_descriptor_manifest import get_static_manifest
from hermes_cli.dev_web_plugin_descriptor_policy import check_descriptor_policy
from hermes_cli.dev_web_plugin_descriptor_schema import (
    FORBIDDEN_PLUGIN_TRUST_LEVELS,
    PLUGIN_TRUST_LEVELS,
    VISIBLE_TRUST_LEVELS,
)

_TRUST_LEVELS = {
    "trusted_builtin_code",
    "trusted_static_descriptor",
    "dev_reviewed_descriptor",
    "experimental_disabled_descriptor",
    "external_forbidden",
    "unknown_forbidden",
    "production_forbidden",
}
_FORBIDDEN_TRUST = {"external_forbidden", "unknown_forbidden", "production_forbidden"}
_VISIBLE_TRUST = {"trusted_builtin_code", "trusted_static_descriptor"}


def _base_entry() -> dict[str, Any]:
    return copy.deepcopy(get_static_manifest()[0])


def _blocked_entry() -> dict[str, Any]:
    return copy.deepcopy(
        next(e for e in get_static_manifest() if e["pluginId"] == "plugin.descriptor.marketplace_blocked")
    )


class TestTrustTaxonomy:
    def test_trust_levels_set_is_frozen(self) -> None:
        assert set(PLUGIN_TRUST_LEVELS) == _TRUST_LEVELS

    def test_forbidden_trust_levels_subset(self) -> None:
        assert set(FORBIDDEN_PLUGIN_TRUST_LEVELS) == _FORBIDDEN_TRUST
        assert FORBIDDEN_PLUGIN_TRUST_LEVELS <= PLUGIN_TRUST_LEVELS

    def test_visible_trust_levels_subset(self) -> None:
        assert set(VISIBLE_TRUST_LEVELS) == _VISIBLE_TRUST
        assert VISIBLE_TRUST_LEVELS <= PLUGIN_TRUST_LEVELS
        # Visible trust levels are disjoint from forbidden trust levels.
        assert VISIBLE_TRUST_LEVELS.isdisjoint(FORBIDDEN_PLUGIN_TRUST_LEVELS)


class TestForbiddenTrustMustBeBlocked:
    @pytest.mark.parametrize("trust", sorted(_FORBIDDEN_TRUST))
    def test_forbidden_trust_with_non_blocked_status_rejected(self, trust: str) -> None:
        entry = _base_entry()
        entry["trustLevel"] = trust
        entry["status"] = "visible"
        errors = check_descriptor_policy(entry)
        assert any("must be blocked" in e.reason for e in errors)

    @pytest.mark.parametrize("trust", sorted(_FORBIDDEN_TRUST))
    def test_forbidden_trust_blocked_is_accepted_for_trust_rule(self, trust: str) -> None:
        entry = _blocked_entry()
        entry["trustLevel"] = trust
        entry["status"] = "blocked"
        entry["blockedReason"] = "blocked_for_policy_test"
        errors = check_descriptor_policy(entry)
        # No trust/status coherence error about "must be blocked".
        assert not any("must be blocked" in e.reason for e in errors if "trustLevel" in e.field)


class TestExperimentalDisabledRestriction:
    def test_experimental_disabled_cannot_be_visible(self) -> None:
        entry = _base_entry()
        entry["trustLevel"] = "experimental_disabled_descriptor"
        entry["status"] = "visible"
        errors = check_descriptor_policy(entry)
        assert any("experimental_disabled_descriptor must be" in e.reason for e in errors)

    def test_experimental_disabled_can_be_disabled(self) -> None:
        entry = _base_entry()
        entry["trustLevel"] = "experimental_disabled_descriptor"
        entry["status"] = "disabled"
        errors = check_descriptor_policy(entry)
        assert not any("experimental_disabled_descriptor must be" in e.reason for e in errors)


class TestVisibleRequiresVerifiedTrust:
    @pytest.mark.parametrize("trust", ["dev_reviewed_descriptor", "experimental_disabled_descriptor"])
    def test_visible_with_non_verified_trust_rejected(self, trust: str) -> None:
        entry = _base_entry()
        entry["trustLevel"] = trust
        entry["status"] = "visible"
        errors = check_descriptor_policy(entry)
        assert any("requires a verified trust level" in e.reason for e in errors)

    def test_visible_with_verified_trust_accepted_for_trust_rule(self) -> None:
        entry = _base_entry()
        entry["trustLevel"] = "trusted_static_descriptor"
        entry["status"] = "visible"
        errors = check_descriptor_policy(entry)
        assert not any("requires a verified trust level" in e.reason for e in errors)


class TestTrustSelfUpgradeRejected:
    def test_binding_forbidden_capability_with_verified_trust_rejected(self) -> None:
        entry = _base_entry()
        entry["capabilityBindings"] = ("capability.forbidden.shell",)
        entry["permissionClass"] = "EXTERNAL_FORBIDDEN"
        entry["trustLevel"] = "trusted_static_descriptor"  # verified → self-upgrade
        entry["status"] = "blocked"
        entry["blockedReason"] = "x"
        errors = check_descriptor_policy(entry)
        assert any("may not carry verified trust level" in e.reason for e in errors)

    def test_binding_forbidden_capability_with_forbidden_trust_ok(self) -> None:
        entry = _blocked_entry()
        # Already external_forbidden trust + blocked + EXTERNAL_FORBIDDEN.
        errors = check_descriptor_policy(entry)
        assert not any("may not carry verified trust level" in e.reason for e in errors)


class TestFirstVersionInvariants:
    def test_every_descriptor_dev_only(self) -> None:
        for entry in get_static_manifest():
            assert entry["devOnly"] is True, entry["pluginId"]

    def test_every_descriptor_production_not_allowed(self) -> None:
        for entry in get_static_manifest():
            assert entry["productionAllowed"] is False, entry["pluginId"]

    def test_every_descriptor_disabled_by_default(self) -> None:
        for entry in get_static_manifest():
            assert entry["disabledByDefault"] is True, entry["pluginId"]

    def test_production_allowed_true_rejected(self) -> None:
        entry = _base_entry()
        entry["productionAllowed"] = True
        errors = check_descriptor_policy(entry)
        assert any("productionAllowed" in e.field for e in errors)

    def test_dev_only_false_rejected(self) -> None:
        entry = _base_entry()
        entry["devOnly"] = False
        errors = check_descriptor_policy(entry)
        assert any("devOnly" in e.field for e in errors)
