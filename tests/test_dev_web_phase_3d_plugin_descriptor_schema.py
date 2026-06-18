"""Phase 3D — Plugin Descriptor Registry Schema tests.

Verifies the frozen taxonomies (plugin trust levels, statuses, execution modes,
sources, permission classes), the allowed/required/forbidden field sets
(including alias + nested variants), the pluginId / capabilityId formats, the
permission-restrictiveness ordering, and the validation predicates.

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_plugin_descriptor_schema import (
    ALLOWED_FIELDS,
    FORBIDDEN_FIELDS,
    FORBIDDEN_PERMISSION_CLASSES,
    FORBIDDEN_PLUGIN_TRUST_LEVELS,
    NON_EXECUTABLE_PLUGIN_STATUSES,
    PERMISSION_CLASSES,
    PERMISSION_RESTRICTIVENESS_ORDER,
    PERMISSION_RESTRICTIVENESS_RANK,
    PLUGIN_EXECUTION_MODES,
    PLUGIN_SOURCES,
    PLUGIN_STATUSES,
    PLUGIN_TRUST_LEVELS,
    REQUIRED_FIELDS,
    VISIBLE_TRUST_LEVELS,
    is_executable_execution_mode,
    is_forbidden_field_present,
    is_terminal_forbidden_permission,
    is_valid_bool,
    is_valid_capability_id,
    is_valid_permission_class,
    is_valid_plugin_execution_mode,
    is_valid_plugin_id,
    is_valid_plugin_source,
    is_valid_plugin_status,
    is_valid_plugin_trust_level,
    most_restrictive_permission,
    permission_rank,
)


class TestFrozenTaxonomies:
    def test_trust_levels_frozen(self) -> None:
        assert PLUGIN_TRUST_LEVELS == frozenset(
            {
                "trusted_builtin_code",
                "trusted_static_descriptor",
                "dev_reviewed_descriptor",
                "experimental_disabled_descriptor",
                "external_forbidden",
                "unknown_forbidden",
                "production_forbidden",
            }
        )

    def test_statuses_frozen(self) -> None:
        assert PLUGIN_STATUSES == frozenset(
            {"planned", "declared", "validated", "visible", "disabled", "blocked", "deprecated", "removed"}
        )

    def test_execution_modes_frozen(self) -> None:
        assert PLUGIN_EXECUTION_MODES == frozenset(
            {"none", "descriptor_only", "read_only_descriptor", "disabled_runtime"}
        )

    def test_sources_frozen(self) -> None:
        assert PLUGIN_SOURCES == frozenset(
            {
                "builtin_static",
                "tracked_static_descriptor",
                "dev_reviewed_descriptor",
                "experimental_disabled",
                "external_forbidden",
                "unknown_forbidden",
                "production_forbidden",
            }
        )

    def test_permission_classes_shared_with_phase_3c(self) -> None:
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

    def test_forbidden_trust_levels_subset(self) -> None:
        assert FORBIDDEN_PLUGIN_TRUST_LEVELS <= PLUGIN_TRUST_LEVELS
        assert FORBIDDEN_PLUGIN_TRUST_LEVELS == frozenset(
            {"external_forbidden", "unknown_forbidden", "production_forbidden"}
        )

    def test_visible_trust_levels_subset(self) -> None:
        assert VISIBLE_TRUST_LEVELS <= PLUGIN_TRUST_LEVELS
        assert VISIBLE_TRUST_LEVELS == frozenset({"trusted_builtin_code", "trusted_static_descriptor"})

    def test_no_executable_status_exists(self) -> None:
        # There is intentionally no installed / loaded / executing status.
        for status in PLUGIN_STATUSES:
            assert status in NON_EXECUTABLE_PLUGIN_STATUSES


class TestRestrictivenessOrdering:
    def test_order_is_most_restrictive_last_indexed(self) -> None:
        # Higher rank == more restrictive. READ_ONLY least, PRODUCTION_FORBIDDEN most.
        assert PERMISSION_RESTRICTIVENESS_ORDER[0] == "READ_ONLY"
        assert PERMISSION_RESTRICTIVENESS_ORDER[-1] == "PRODUCTION_FORBIDDEN"

    def test_rank_map_complete(self) -> None:
        for cls in PERMISSION_CLASSES:
            assert cls in PERMISSION_RESTRICTIVENESS_RANK

    def test_permission_rank_values(self) -> None:
        assert permission_rank("READ_ONLY") == 0
        assert permission_rank("PRODUCTION_FORBIDDEN") == 7
        assert permission_rank("EXTERNAL_FORBIDDEN") > permission_rank("ADMIN_FORBIDDEN")
        assert permission_rank("ADMIN_FORBIDDEN") > permission_rank("WRITE_CONFIRM")

    def test_permission_rank_unknown(self) -> None:
        assert permission_rank("not_a_class") == -1
        assert permission_rank(None) == -1

    def test_most_restrictive_single(self) -> None:
        assert most_restrictive_permission(["READ_ONLY"]) == "READ_ONLY"
        assert most_restrictive_permission(["EXTERNAL_FORBIDDEN"]) == "EXTERNAL_FORBIDDEN"

    def test_most_restrictive_multiple(self) -> None:
        # READ_ONLY + WRITE_CONFIRM + EXTERNAL_FORBIDDEN → EXTERNAL_FORBIDDEN.
        result = most_restrictive_permission(["READ_ONLY", "WRITE_CONFIRM", "EXTERNAL_FORBIDDEN"])
        assert result == "EXTERNAL_FORBIDDEN"

    def test_most_restrictive_empty_or_invalid(self) -> None:
        assert most_restrictive_permission([]) is None
        assert most_restrictive_permission(None) is None
        assert most_restrictive_permission(["bogus"]) is None


class TestFieldSets:
    def test_required_fields_subset_of_allowed(self) -> None:
        for field in REQUIRED_FIELDS:
            assert field in ALLOWED_FIELDS

    def test_capability_bindings_in_required(self) -> None:
        assert "capabilityBindings" in REQUIRED_FIELDS

    def test_forbidden_fields_disjoint_from_allowed(self) -> None:
        assert not (FORBIDDEN_FIELDS & set(ALLOWED_FIELDS))

    def test_forbidden_fields_include_canonical_surface(self) -> None:
        for name in (
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
            "localPath",
            "remoteUrl",
            "installCommand",
            "postInstallHook",
            "preExecutionHook",
            "arbitraryArgs",
        ):
            assert name in FORBIDDEN_FIELDS

    def test_forbidden_fields_include_alias_variants(self) -> None:
        for name in (
            "authorization",
            "AUTHORIZATION",
            "bearer",
            "Bearer",
            "api_key",
            "secretValue",
            "token",
            "accessToken",
            "callable_repr",
            "shell_command",
            "sql",
            "production_path",
            "dynamic_import",
            "importPath",
            "modulePath",
            "external_url",
            "download_url",
            "install_command",
            "post_install_hook",
            "pre_execution_hook",
        ):
            assert name in FORBIDDEN_FIELDS


class TestValidationPredicates:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("trusted_static_descriptor", True),
            ("dev_reviewed_descriptor", True),
            ("external_forbidden", True),
            ("production_forbidden", True),
            ("TRUSTED_STATIC_DESCRIPTOR", False),
            ("trusted", False),
            (None, False),
            (123, False),
        ],
    )
    def test_is_valid_plugin_trust_level(self, value: object, expected: bool) -> None:
        assert is_valid_plugin_trust_level(value) is expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("visible", True),
            ("disabled", True),
            ("blocked", True),
            ("installed", False),  # no runtime lifecycle status
            ("loaded", False),
            ("executing", False),
            (None, False),
        ],
    )
    def test_is_valid_plugin_status(self, value: object, expected: bool) -> None:
        assert is_valid_plugin_status(value) is expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("descriptor_only", True),
            ("disabled_runtime", True),
            ("none", True),
            ("confirmed_execute", False),  # capability execution mode, not allowed here
            ("manual_live", False),
            (None, False),
        ],
    )
    def test_is_valid_plugin_execution_mode(self, value: object, expected: bool) -> None:
        assert is_valid_plugin_execution_mode(value) is expected

    def test_no_execution_mode_is_executable(self) -> None:
        for mode in PLUGIN_EXECUTION_MODES:
            assert is_executable_execution_mode(mode) is False

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("plugin.descriptor.registry_status", True),
            ("plugin.descriptor.a", True),
            ("plugin", False),  # no dot segment
            ("Plugin.Descriptor", False),  # uppercase
            ("plugin..x", False),
            ("", False),
            (None, False),
        ],
    )
    def test_is_valid_plugin_id(self, value: object, expected: bool) -> None:
        assert is_valid_plugin_id(value) is expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("registry.capability_registry_status", True),
            ("tool.read.route_governance_read", True),
            ("Registry.X", False),
            ("nope", False),
            (None, False),
        ],
    )
    def test_is_valid_capability_id(self, value: object, expected: bool) -> None:
        assert is_valid_capability_id(value) is expected

    def test_is_valid_bool_strict(self) -> None:
        assert is_valid_bool(True) is True
        assert is_valid_bool(False) is True
        assert is_valid_bool(1) is False  # int is not bool
        assert is_valid_bool("true") is False

    def test_is_terminal_forbidden_permission(self) -> None:
        assert is_terminal_forbidden_permission("ADMIN_FORBIDDEN") is True
        assert is_terminal_forbidden_permission("EXTERNAL_FORBIDDEN") is True
        assert is_terminal_forbidden_permission("PRODUCTION_FORBIDDEN") is True
        assert is_terminal_forbidden_permission("READ_ONLY") is False
        assert FORBIDDEN_PERMISSION_CLASSES == frozenset(
            {"ADMIN_FORBIDDEN", "EXTERNAL_FORBIDDEN", "PRODUCTION_FORBIDDEN"}
        )


class TestForbiddenFieldScan:
    def test_top_level_forbidden_field_detected(self) -> None:
        assert is_forbidden_field_present({"pluginId": "x.y", "shellCommand": "rm -rf"}) == "shellCommand"

    def test_no_forbidden_field(self) -> None:
        assert is_forbidden_field_present({"pluginId": "x.y", "displayName": "ok"}) is None

    def test_non_dict_returns_none(self) -> None:
        assert is_forbidden_field_present("not a dict") is None
        assert is_forbidden_field_present(None) is None

    def test_nested_forbidden_field_detected(self) -> None:
        entry = {
            "pluginId": "x.y",
            "metadataSchema": {"innocent": True, "Authorization": "Bearer abc"},
        }
        assert is_forbidden_field_present(entry) == "Authorization"

    def test_deeply_nested_forbidden_field_detected(self) -> None:
        entry = {
            "pluginId": "x.y",
            "metadataSchema": {"layer": [{"callable": "evil"}]},
        }
        assert is_forbidden_field_present(entry) == "callable"

    def test_alias_forbidden_field_detected(self) -> None:
        assert is_forbidden_field_present({"pluginId": "x.y", "bearer": "abc"}) == "bearer"
        assert is_forbidden_field_present({"pluginId": "x.y", "api_key": "abc"}) == "api_key"
        assert is_forbidden_field_present({"pluginId": "x.y", "install_command": "x"}) == "install_command"
