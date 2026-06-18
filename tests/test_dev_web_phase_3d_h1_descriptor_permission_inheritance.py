"""Phase 3D-H1 — Permission inheritance / most-restrictive rule / no escalation.

Hardens Lens 4: a descriptor inherits the **most-restrictive** permission class
among its bound Phase 3C capabilities and may never declare a less-restrictive
class (escalation is rejected fail-closed). The restrictiveness ordering is
frozen and shared with the Phase 3C taxonomy.

Phase: 3D-H1 — Static Plugin Descriptor Registry Hardening
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from hermes_cli.dev_web_plugin_descriptor_manifest import get_static_manifest
from hermes_cli.dev_web_plugin_descriptor_policy import (
    build_capability_index,
    check_descriptor_policy,
    inherited_permission_class,
)
from hermes_cli.dev_web_plugin_descriptor_schema import (
    FORBIDDEN_PERMISSION_CLASSES,
    PERMISSION_CLASSES,
    PERMISSION_RESTRICTIVENESS_ORDER,
    PERMISSION_RESTRICTIVENESS_RANK,
    is_terminal_forbidden_permission,
    most_restrictive_permission,
    permission_rank,
)

_EXPECTED_ORDER: tuple[str, ...] = (
    "READ_ONLY",            # 0
    "WRITE_PREVIEW",        # 1
    "WRITE_CONFIRM",        # 2
    "ROLLBACK_CONFIRM",     # 3
    "LIVE_PROVIDER_GATED",  # 4
    "ADMIN_FORBIDDEN",      # 5
    "EXTERNAL_FORBIDDEN",   # 6
    "PRODUCTION_FORBIDDEN",  # 7
)


def _base_entry() -> dict[str, Any]:
    return copy.deepcopy(get_static_manifest()[0])


class TestRestrictivenessOrder:
    def test_order_is_frozen_most_restrictive_last(self) -> None:
        assert PERMISSION_RESTRICTIVENESS_ORDER == _EXPECTED_ORDER

    def test_rank_map_matches_order(self) -> None:
        for rank, cls in enumerate(PERMISSION_RESTRICTIVENESS_ORDER):
            assert PERMISSION_RESTRICTIVENESS_RANK[cls] == rank

    def test_every_permission_class_has_a_rank(self) -> None:
        for cls in PERMISSION_CLASSES:
            assert cls in PERMISSION_RESTRICTIVENESS_RANK

    @pytest.mark.parametrize("cls", _EXPECTED_ORDER)
    def test_permission_rank_increasing(self, cls: str) -> None:
        assert permission_rank(cls) == _EXPECTED_ORDER.index(cls)

    def test_unknown_class_ranks_minus_one(self) -> None:
        assert permission_rank("TOTALLY_MADE_UP") == -1
        assert permission_rank(None) == -1
        assert permission_rank(123) == -1


class TestMostRestrictivePermission:
    def test_empty_returns_none(self) -> None:
        assert most_restrictive_permission([]) is None
        assert most_restrictive_permission(()) is None
        assert most_restrictive_permission(None) is None

    def test_single_returns_that_class(self) -> None:
        assert most_restrictive_permission(["READ_ONLY"]) == "READ_ONLY"
        assert most_restrictive_permission(["PRODUCTION_FORBIDDEN"]) == "PRODUCTION_FORBIDDEN"

    def test_picks_highest_rank_among_many(self) -> None:
        assert most_restrictive_permission(["READ_ONLY", "WRITE_CONFIRM"]) == "WRITE_CONFIRM"
        assert (
            most_restrictive_permission(["WRITE_CONFIRM", "READ_ONLY", "EXTERNAL_FORBIDDEN"])
            == "EXTERNAL_FORBIDDEN"
        )

    def test_production_forbidden_dominates_all(self) -> None:
        assert (
            most_restrictive_permission(list(_EXPECTED_ORDER)) == "PRODUCTION_FORBIDDEN"
        )

    def test_unknown_classes_ignored(self) -> None:
        assert most_restrictive_permission(["READ_ONLY", "BOGUS"]) == "READ_ONLY"


class TestInheritedPermissionExactness:
    def test_single_binding_inherits_exactly(self) -> None:
        index = build_capability_index()
        # registry.capability_registry_status is READ_ONLY.
        inherited = inherited_permission_class(("registry.capability_registry_status",), index)
        assert inherited == "READ_ONLY"

    def test_multiple_bindings_inherit_most_restrictive(self) -> None:
        index = build_capability_index()
        # sandbox_write_preview_bridge binds WRITE_CONFIRM capabilities.
        inherited = inherited_permission_class(
            (
                "tool.sandbox.dev_sandbox_file_write",
                "tool.sandbox.dev_sandbox_file_append",
                "tool.sandbox.dev_sandbox_file_patch",
            ),
            index,
        )
        assert inherited == "WRITE_CONFIRM"

    def test_blocked_descriptor_inherits_external_forbidden(self) -> None:
        index = build_capability_index()
        inherited = inherited_permission_class(
            (
                "capability.forbidden.external_http",
                "capability.forbidden.shell",
                "capability.forbidden.database_mutation",
            ),
            index,
        )
        assert inherited == "EXTERNAL_FORBIDDEN"
        assert is_terminal_forbidden_permission(inherited)


class TestEscalationRejected:
    @pytest.mark.parametrize(
        "declared,inherited_cap",
        [
            ("READ_ONLY", "tool.sandbox.dev_sandbox_file_write"),      # WRITE_CONFIRM
            ("WRITE_PREVIEW", "tool.sandbox.dev_sandbox_file_append"),  # WRITE_CONFIRM
            ("READ_ONLY", "capability.forbidden.shell"),               # EXTERNAL_FORBIDDEN
        ],
    )
    def test_declaring_less_restrictive_is_escalation(
        self, declared: str, inherited_cap: str
    ) -> None:
        entry = _base_entry()
        entry["capabilityBindings"] = (inherited_cap,)
        entry["permissionClass"] = declared
        errors = check_descriptor_policy(entry)
        assert any("permission escalation" in e.reason for e in errors)

    def test_descriptor_cannot_weaken_inherited_class(self) -> None:
        # Declaring READ_ONLY when inheriting EXTERNAL_FORBIDDEN is rejected.
        entry = _base_entry()
        entry["capabilityBindings"] = ("capability.forbidden.remote_registry",)
        entry["permissionClass"] = "READ_ONLY"
        errors = check_descriptor_policy(entry)
        assert any("permission escalation" in e.reason for e in errors)

    def test_production_forbidden_cannot_be_upgraded(self) -> None:
        entry = _base_entry()
        entry["capabilityBindings"] = ("capability.forbidden.production_operation",)
        entry["permissionClass"] = "READ_ONLY"
        errors = check_descriptor_policy(entry)
        assert any("permission escalation" in e.reason for e in errors)

    def test_terminal_forbidden_classes_are_non_executable(self) -> None:
        for cls in FORBIDDEN_PERMISSION_CLASSES:
            assert is_terminal_forbidden_permission(cls) is True
