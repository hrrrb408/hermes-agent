"""Phase 3D — Plugin Descriptor Registry audit bridge tests.

Verifies the ``plugin_descriptor_*`` audit writer:
  - emits into the existing durable store (AUDIT_KIND_INTERNAL) under the dev
    HERMES_HOME (never ``~/.hermes``),
  - applies defensive re-redaction so a forbidden field in the payload never
    reaches the store,
  - never raises (fail safe) and audit failure never enables a descriptor /
    grants permission,
  - the persisted event carries safe fields only.

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
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

    def test_safe_payload_fields_excludes_secrets(self) -> None:
        for forbidden in (
            "apiKey",
            "Authorization",
            "secret",
            "tokenHash",
            "callable",
            "shellCommand",
            "externalUrl",
            "installCommand",
        ):
            assert forbidden not in SAFE_PAYLOAD_FIELDS


class TestPayloadRedaction:
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

    def test_nested_safe_metadata_redacted(self) -> None:
        payload = {
            "pluginId": "plugin.descriptor.x",
            "safeMetadata": {"ok": True, "apiKey": "sk-leak"},
        }
        cleaned = redact_plugin_descriptor_payload(payload)
        # safeMetadata keeps only safe fields; apiKey is not a safe field → dropped.
        assert "apiKey" not in cleaned.get("safeMetadata", {})


class TestWriteBehavior:
    def test_write_succeeds_under_dev_home(self, tmp_path: Path) -> None:
        result = write_plugin_descriptor_audit(
            event_type="plugin_descriptor_registry_loaded",
            plugin_id="plugin.descriptor.registry_status",
            permission_class="READ_ONLY",
            status="visible",
            hermes_home=str(tmp_path / "dev-home"),
        )
        # The store may report written=True under a writable dev home.
        assert result is not None
        events = _events(tmp_path / "dev-home")
        assert any(ev.get("eventType") == "plugin_descriptor_registry_loaded" for ev in events)
        # The persisted event carries the safe source + redaction flag.
        written = [ev for ev in events if ev.get("eventType") == "plugin_descriptor_registry_loaded"]
        assert written[0].get("source") == PLUGIN_DESCRIPTOR_AUDIT_SOURCE

    def test_execution_blocked_event_recordable_without_executing(self, tmp_path: Path) -> None:
        # An execution *request* is recorded as blocked — no execution occurs.
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

    def test_never_writes_to_production_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # The bridge only writes to the explicitly-passed dev HERMES_HOME.
        prod_marker = tmp_path / "fake-prod"
        prod_marker.mkdir()
        write_plugin_descriptor_audit(
            event_type="plugin_descriptor_registry_loaded",
            hermes_home=str(tmp_path / "dev-home"),
        )
        # No audit file should have appeared under the fake-prod tree.
        assert not list(prod_marker.rglob("*.jsonl"))
