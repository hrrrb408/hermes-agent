"""Phase 3C-H1 — Schema Forbidden Fields / Validation Fail-closed Hardening.

Hardens ``CAP-FORBIDDEN-FIELDS-3C-H1-001`` (Lens 2).

A forbidden field would convert a *descriptive* registry into an *execution*
surface (dynamic code load, shell, SQL mutation, network fetch, secret
carriage). This test proves validation rejects every forbidden field — at the
top level, via case/alias variants, AND nested inside an allowed field's
value (the leak closed by HARDENING-3C-H1-001) — and that the read model
never exposes a forbidden field even when a caller feeds an unvalidated,
crafted manifest. Fail-closed: an invalid manifest yields
``status=validation_failed`` and blocked details.

Phase: 3C-H1 — Static Capability Registry Hardening
Status: implemented
"""

from __future__ import annotations

import copy
import json

import pytest

from hermes_cli.dev_web_capability_registry import (
    build_registry_summary,
    get_capability_detail,
    list_capability_details,
    validate_manifest,
)
from hermes_cli.dev_web_capability_registry_manifest import get_static_manifest
from hermes_cli.dev_web_capability_registry_schema import (
    FORBIDDEN_FIELDS,
    is_forbidden_field_present,
)


def _good_entry(cid: str = "tool.read.example_read") -> dict:
    base = copy.deepcopy(list(get_static_manifest())[0])
    base["capabilityId"] = cid
    return base


_LEAK_TOKENS = (
    "apiKey",
    "Authorization",
    "Bearer",
    "shellCommand",
    "pythonImportPath",
    "externalUrl",
    "downloadUrl",
    "pluginPackage",
    "dynamicModule",
    "evalCode",
    "execCode",
    "sqlStatement",
    "productionPath",
    "callable",
    "secret",
)


def _assert_no_leak(blob: str) -> None:
    for token in _LEAK_TOKENS:
        assert token not in blob, f"forbidden token {token!r} leaked"


class TestTopLevelForbiddenFields:
    def test_every_forbidden_field_rejected(self) -> None:
        for field_name in FORBIDDEN_FIELDS:
            entry = _good_entry()
            entry[field_name] = "evil-payload"
            report = validate_manifest([entry])
            assert not report.valid, f"forbidden field {field_name} not rejected"

    def test_forbidden_field_blocks_detail_read_model(self) -> None:
        entry = _good_entry()
        entry["shellCommand"] = "rm -rf /"
        details = list_capability_details([entry])
        assert details[0]["status"] == "blocked"
        _assert_no_leak(json.dumps(details))

    def test_is_forbidden_field_present_shallow(self) -> None:
        assert is_forbidden_field_present({"shellCommand": "x"}) == "shellCommand"
        assert is_forbidden_field_present({"capabilityId": "x.y"}) is None
        assert is_forbidden_field_present("nope") is None


class TestAliasForbiddenFields:
    """Case / alias variants a smuggler might try. All must be rejected
    fail-closed (via the forbidden scan or the unknown-field whitelist)."""

    @pytest.mark.parametrize(
        "alias",
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
        ],
    )
    def test_alias_rejected_fail_closed(self, alias: str) -> None:
        entry = _good_entry()
        entry[alias] = "smuggled"
        report = validate_manifest([entry])
        assert not report.valid, f"alias field {alias!r} was accepted"
        # And the read model never exposes the alias value.
        detail = list_capability_details([entry])[0]
        assert alias not in json.dumps(detail)


class TestNestedForbiddenFields:
    """The leak closed by HARDENING-3C-H1-001: a forbidden field nested inside
    an allowed field's value (dict or list) must be detected and blocked."""

    def test_nested_dict_forbidden_field_detected_by_scanner(self) -> None:
        entry = {
            "capabilityId": "x.y.z",
            "metadataSchema": {"shellCommand": "rm -rf", "secret": "k"},
        }
        assert is_forbidden_field_present(entry) == "shellCommand"

    def test_nested_list_forbidden_field_detected_by_scanner(self) -> None:
        entry = {"capabilityId": "x.y.z", "metadataSchema": [{"sqlStatement": "DROP"}]}
        assert is_forbidden_field_present(entry) == "sqlStatement"

    def test_deeply_nested_forbidden_field_detected(self) -> None:
        entry = {
            "capabilityId": "x.y.z",
            "metadataSchema": {"a": {"b": [{"Authorization": "Bearer x"}]}},
        }
        assert is_forbidden_field_present(entry) == "Authorization"

    def test_nested_dict_forbidden_field_rejected_in_validation(self) -> None:
        entry = _good_entry()
        entry["metadataSchema"] = {"shellCommand": "rm -rf", "secret": "leak"}
        report = validate_manifest([entry])
        assert not report.valid

    def test_nested_list_forbidden_field_rejected_in_validation(self) -> None:
        entry = _good_entry()
        entry["metadataSchema"] = [{"sqlStatement": "DROP TABLE users"}]
        report = validate_manifest([entry])
        assert not report.valid

    def test_nested_forbidden_field_blocks_read_model_no_leak(self) -> None:
        entry = _good_entry()
        entry["metadataSchema"] = {
            "shellCommand": "rm -rf",
            "secret": "leak",
            "Authorization": "Bearer x",
        }
        details = list_capability_details([entry])
        assert details[0]["status"] == "blocked"
        _assert_no_leak(json.dumps(details))

    def test_nested_forbidden_field_blocks_single_detail_no_leak(self) -> None:
        entry = _good_entry("tool.read.nested_probe")
        entry["blockedReason"] = [{"productionPath": "/etc/passwd"}]
        detail = get_capability_detail([entry], "tool.read.nested_probe")
        assert detail is not None
        assert detail["status"] == "blocked"
        _assert_no_leak(json.dumps(detail))

    def test_benign_nested_structure_also_rejected(self) -> None:
        # Even a nested dict with no forbidden key is rejected — scalar fields
        # must be scalar strings, never nested structures.
        entry = _good_entry()
        entry["metadataSchema"] = {"note": "harmless but nested"}
        report = validate_manifest([entry])
        assert not report.valid


class TestFailClosedSummary:
    def test_invalid_manifest_summary_validation_failed(self) -> None:
        bad = _good_entry()
        bad["pythonImportPath"] = "evil"
        report = validate_manifest([bad])
        summary = build_registry_summary(report)
        assert summary["status"] == "validation_failed"
        assert summary["validationPassed"] is False
        assert summary["loaded"] is False

    def test_invalid_manifest_not_exposed_as_enabled(self) -> None:
        bad = _good_entry()
        bad["secret"] = "leak"
        report = validate_manifest([bad])
        summary = build_registry_summary(report)
        assert summary["status"] != "enabled"

    def test_blocked_count_includes_blocked_entries(self) -> None:
        blocked = _good_entry()
        blocked["status"] = "blocked"
        blocked["permissionClass"] = "ADMIN_FORBIDDEN"
        blocked["trustLevel"] = "EXPERIMENTAL_DISABLED"
        blocked["executionMode"] = "none"
        blocked["routeExposure"] = "forbidden_new_route"
        blocked["blockedReason"] = "test_blocked"
        report = validate_manifest([blocked])
        assert report.blocked_count == 1
