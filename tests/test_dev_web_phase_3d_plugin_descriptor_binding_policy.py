"""Phase 3D — Plugin Descriptor capability-binding + permission-inheritance tests.

Verifies a descriptor binds only to existing Phase 3C capabilityIds, inherits
the most-restrictive permission class among its bindings, cannot escalate
permission (declare a less-restrictive class than inherited), cannot introduce
a new capabilityId or permission class, and cannot mark a forbidden-bound
descriptor as visible.

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_plugin_descriptor_policy import (
    build_capability_index,
    check_descriptor_policy,
    inherited_permission_class,
    most_restrictive_permission,
    permission_rank,
)
from hermes_cli.dev_web_plugin_descriptor_registry import validate_manifest

_INDEX = build_capability_index()


def _entry(**overrides: object) -> dict:
    base: dict = {
        "pluginId": "plugin.descriptor.binding_test",
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


class TestCapabilityIndex:
    def test_index_built_from_phase_3c(self) -> None:
        assert "registry.capability_registry_status" in _INDEX
        assert _INDEX["registry.capability_registry_status"] == "READ_ONLY"

    def test_index_contains_forbidden_capabilities(self) -> None:
        assert _INDEX["capability.forbidden.dynamic_plugin_load"] == "EXTERNAL_FORBIDDEN"
        assert _INDEX["capability.forbidden.production_operation"] == "PRODUCTION_FORBIDDEN"
        assert _INDEX["capability.forbidden.shell"] == "ADMIN_FORBIDDEN"

    def test_index_nonempty(self) -> None:
        assert len(_INDEX) > 30


class TestInheritedPermission:
    def test_single_binding_inherits_its_class(self) -> None:
        assert inherited_permission_class(["registry.capability_registry_detail"], _INDEX) == "READ_ONLY"

    def test_multiple_bindings_most_restrictive(self) -> None:
        # external_http (EXTERNAL_FORBIDDEN) + shell (ADMIN_FORBIDDEN) + db (ADMIN)
        result = inherited_permission_class(
            [
                "capability.forbidden.external_http",
                "capability.forbidden.shell",
                "capability.forbidden.database_mutation",
            ],
            _INDEX,
        )
        assert result == "EXTERNAL_FORBIDDEN"

    def test_unknown_capability_returns_none(self) -> None:
        assert inherited_permission_class(["does.not.exist"], _INDEX) is None

    def test_empty_or_invalid_returns_none(self) -> None:
        assert inherited_permission_class([], _INDEX) is None
        assert inherited_permission_class(None, _INDEX) is None
        assert inherited_permission_class([123], _INDEX) is None


class TestPermissionEscalationRejected:
    def test_declared_less_restrictive_than_inherited_rejected(self) -> None:
        # Bound to EXTERNAL_FORBIDDEN but declared READ_ONLY → escalation.
        entry = _entry(
            capabilityBindings=("capability.forbidden.marketplace",),
            permissionClass="READ_ONLY",
            trustLevel="external_forbidden",
            source="external_forbidden",
            status="blocked",
            blockedReason="x",
        )
        errors = check_descriptor_policy(entry, _INDEX)
        assert any("escalation" in e.reason for e in errors)

    def test_declared_equals_inherited_accepted(self) -> None:
        entry = _entry(
            capabilityBindings=("registry.capability_registry_detail",),
            permissionClass="READ_ONLY",
        )
        errors = check_descriptor_policy(entry, _INDEX)
        assert errors == []

    def test_static_manifest_no_escalation(self) -> None:
        from hermes_cli.dev_web_plugin_descriptor_manifest import get_static_manifest

        report = validate_manifest(get_static_manifest())
        assert report.valid
        assert not any("escalation" in e.reason for e in report.errors)


class TestNoNewCapabilityOrPermission:
    def test_unknown_capability_binding_rejected(self) -> None:
        entry = _entry(capabilityBindings=("does.not.exist",))
        errors = check_descriptor_policy(entry, _INDEX)
        assert any("does not exist" in e.reason for e in errors)

    def test_new_permission_class_rejected_at_schema(self) -> None:
        # A bogus permissionClass is rejected by enum validation in the loader.
        entry = _entry(permissionClass="SUPER_USER")
        report = validate_manifest([entry])
        assert not report.valid
        assert any(e.field == "permissionClass" for e in report.errors)


class TestForbiddenBindingCannotBeVisible:
    def test_forbidden_bound_descriptor_cannot_be_visible(self) -> None:
        entry = _entry(
            capabilityBindings=("capability.forbidden.marketplace",),
            permissionClass="EXTERNAL_FORBIDDEN",
            trustLevel="external_forbidden",
            source="external_forbidden",
            status="visible",  # wrong — must be blocked
        )
        errors = check_descriptor_policy(entry, _INDEX)
        assert any("must be blocked" in e.reason for e in errors)

    def test_forbidden_bound_descriptor_blocked_accepted(self) -> None:
        entry = _entry(
            capabilityBindings=("capability.forbidden.marketplace",),
            permissionClass="EXTERNAL_FORBIDDEN",
            trustLevel="external_forbidden",
            source="external_forbidden",
            status="blocked",
            blockedReason="marketplace_is_forbidden",
        )
        errors = check_descriptor_policy(entry, _INDEX)
        assert errors == []


class TestMostRestrictiveHelper:
    def test_production_most_restrictive(self) -> None:
        assert (
            most_restrictive_permission(["READ_ONLY", "PRODUCTION_FORBIDDEN", "ADMIN_FORBIDDEN"])
            == "PRODUCTION_FORBIDDEN"
        )

    def test_rank_ordering(self) -> None:
        assert permission_rank("PRODUCTION_FORBIDDEN") > permission_rank("EXTERNAL_FORBIDDEN")
        assert permission_rank("EXTERNAL_FORBIDDEN") > permission_rank("READ_ONLY")
