"""Phase 3C — Capability Registry Schema tests.

Verifies the frozen taxonomies (categories, statuses, permission classes, trust
levels, execution modes, route exposures, sources), the allowed/required/
forbidden field sets, the capabilityId format, and the validation predicates.

Phase: 3C — Static dev-only Capability Registry
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_capability_registry_schema import (
    ALLOWED_FIELDS,
    CAPABILITY_STATUSES,
    CATEGORIES,
    EXECUTION_MODES,
    FORBIDDEN_FIELDS,
    FORBIDDEN_PERMISSION_CLASSES,
    FORBIDDEN_TRUST_LEVELS,
    PERMISSION_CLASSES,
    REQUIRED_FIELDS,
    ROUTE_EXPOSURES,
    TRUST_LEVELS,
    is_executable_status,
    is_forbidden_field_present,
    is_terminal_forbidden,
    is_valid_bool,
    is_valid_capability_id,
    is_valid_category,
    is_valid_execution_mode,
    is_valid_permission_class,
    is_valid_route_exposure,
    is_valid_source,
    is_valid_status,
    is_valid_trust_level,
)


class TestFrozenTaxonomies:
    def test_categories_frozen(self) -> None:
        assert CATEGORIES == frozenset(
            {"tool", "provider", "workflow", "sandbox", "audit", "registry", "system"}
        )

    def test_statuses_frozen(self) -> None:
        assert CAPABILITY_STATUSES == frozenset(
            {"enabled", "disabled", "blocked", "planned", "deprecated"}
        )

    def test_permission_classes_frozen(self) -> None:
        assert PERMISSION_CLASSES == frozenset(
            {
                "READ_ONLY",
                "WRITE_PREVIEW",
                "WRITE_CONFIRM",
                "ROLLBACK_CONFIRM",
                "LIVE_PROVIDER_GATED",
                "ADMIN_FORBIDDEN",
                "EXTERNAL_FORBIDDEN",
                "PRODUCTION_FORBIDDEN",
            }
        )

    def test_trust_levels_frozen(self) -> None:
        assert TRUST_LEVELS == frozenset(
            {
                "BUILTIN_VERIFIED",
                "DEV_STATIC_MANIFEST",
                "EXPERIMENTAL_DISABLED",
                "EXTERNAL_FORBIDDEN",
                "UNKNOWN_FORBIDDEN",
            }
        )

    def test_execution_modes_frozen(self) -> None:
        assert EXECUTION_MODES == frozenset(
            {"none", "read_only", "dry_run", "confirmed_execute", "manual_live"}
        )

    def test_route_exposures_frozen(self) -> None:
        assert ROUTE_EXPOSURES == frozenset(
            {"existing_route_only", "no_route", "forbidden_new_route"}
        )

    def test_forbidden_permission_classes_terminal(self) -> None:
        assert FORBIDDEN_PERMISSION_CLASSES == frozenset(
            {"ADMIN_FORBIDDEN", "EXTERNAL_FORBIDDEN", "PRODUCTION_FORBIDDEN"}
        )
        assert FORBIDDEN_TRUST_LEVELS == frozenset(
            {"EXTERNAL_FORBIDDEN", "UNKNOWN_FORBIDDEN"}
        )


class TestPredicates:
    @pytest.mark.parametrize("value", ["tool", "provider", "registry", "system"])
    def test_valid_category(self, value: str) -> None:
        assert is_valid_category(value)

    @pytest.mark.parametrize("value", ["", "unknown", None, 1])
    def test_invalid_category(self, value) -> None:
        assert not is_valid_category(value)

    @pytest.mark.parametrize("value", ["enabled", "blocked"])
    def test_valid_status(self, value: str) -> None:
        assert is_valid_status(value)

    def test_invalid_status(self) -> None:
        assert not is_valid_status("active")

    @pytest.mark.parametrize(
        "value", ["READ_ONLY", "WRITE_CONFIRM", "LIVE_PROVIDER_GATED", "ADMIN_FORBIDDEN"]
    )
    def test_valid_permission_class(self, value: str) -> None:
        assert is_valid_permission_class(value)

    def test_invalid_permission_class(self) -> None:
        assert not is_valid_permission_class("SUPER_USER")

    def test_valid_trust_level(self) -> None:
        assert is_valid_trust_level("BUILTIN_VERIFIED")

    def test_invalid_trust_level(self) -> None:
        assert not is_valid_trust_level("TRUSTED_REMOTE")

    def test_valid_execution_mode(self) -> None:
        assert is_valid_execution_mode("manual_live")

    def test_invalid_execution_mode(self) -> None:
        assert not is_valid_execution_mode("auto_run")

    def test_valid_route_exposure(self) -> None:
        assert is_valid_route_exposure("no_route")

    def test_invalid_route_exposure(self) -> None:
        assert not is_valid_route_exposure("new_route_allowed")

    def test_valid_source(self) -> None:
        assert is_valid_source("builtin")
        assert is_valid_source("static_manifest")

    def test_invalid_source(self) -> None:
        assert not is_valid_source("remote_marketplace")

    def test_valid_capability_id_format(self) -> None:
        assert is_valid_capability_id("tool.read.route_governance_read")
        assert is_valid_capability_id("capability.forbidden.shell")

    @pytest.mark.parametrize(
        "value", ["single", "UPPER.CASE", "tool..double", ".leading", "trailing.", "with space.x"]
    )
    def test_invalid_capability_id(self, value: str) -> None:
        assert not is_valid_capability_id(value)

    def test_capability_id_rejects_non_string(self) -> None:
        assert not is_valid_capability_id(None)
        assert not is_valid_capability_id(123)

    def test_is_valid_bool(self) -> None:
        assert is_valid_bool(True)
        assert is_valid_bool(False)
        assert not is_valid_bool("true")
        assert not is_valid_bool(1)

    def test_is_terminal_forbidden(self) -> None:
        assert is_terminal_forbidden("ADMIN_FORBIDDEN")
        assert is_terminal_forbidden("EXTERNAL_FORBIDDEN")
        assert is_terminal_forbidden("PRODUCTION_FORBIDDEN")
        assert not is_terminal_forbidden("READ_ONLY")

    def test_is_executable_status(self) -> None:
        assert is_executable_status("enabled")
        assert not is_executable_status("blocked")
        assert not is_executable_status("disabled")


class TestFieldSets:
    def test_required_fields_minimal(self) -> None:
        assert set(REQUIRED_FIELDS) == {
            "capabilityId",
            "category",
            "permissionClass",
            "trustLevel",
            "status",
        }

    def test_required_subset_of_allowed(self) -> None:
        for field_name in REQUIRED_FIELDS:
            assert field_name in ALLOWED_FIELDS

    def test_forbidden_fields_disjoint_from_allowed(self) -> None:
        # No forbidden field may also be an allowed field.
        assert FORBIDDEN_FIELDS.isdisjoint(set(ALLOWED_FIELDS))

    def test_forbidden_fields_complete(self) -> None:
        assert FORBIDDEN_FIELDS == frozenset(
            {
                "pythonImportPath",
                "callable",
                "shellCommand",
                "externalUrl",
                "downloadUrl",
                "pluginPackage",
                "dynamicModule",
                "evalCode",
                "execCode",
                "sqlStatement",
                "productionPath",
                "apiKey",
                "Authorization",
                "secret",
            }
        )

    def test_is_forbidden_field_present_detects(self) -> None:
        entry = {"capabilityId": "x.y", "shellCommand": "rm -rf /"}
        assert is_forbidden_field_present(entry) == "shellCommand"

    def test_is_forbidden_field_present_clean(self) -> None:
        entry = {"capabilityId": "x.y", "status": "blocked"}
        assert is_forbidden_field_present(entry) is None

    def test_is_forbidden_field_present_non_dict(self) -> None:
        assert is_forbidden_field_present("not a dict") is None
