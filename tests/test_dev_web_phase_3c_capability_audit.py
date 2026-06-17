"""Phase 3C — Capability Registry audit bridge tests.

Verifies the ``capability_registry_*`` audit writer:
  - emits into the existing durable store (AUDIT_KIND_INTERNAL) under the dev
    HERMES_HOME (never ``~/.hermes``),
  - applies defensive re-redaction so a forbidden field in the payload never
    reaches the store,
  - never raises (fail safe) and audit failure never enables a capability,
  - the persisted event carries safe fields only.

Phase: 3C — Static dev-only Capability Registry
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_audit_store import get_audit_store_root, iter_all_events
from hermes_cli.dev_web_capability_registry_audit import (
    CAPABILITY_REGISTRY_AUDIT_SOURCE,
    CAPABILITY_REGISTRY_EVENT_TYPES,
    SAFE_PAYLOAD_FIELDS,
    redact_capability_registry_payload,
    write_capability_registry_audit)

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
    return [
        ev
        for ev in (row[2] for row in iter_all_events(root))
        if isinstance(ev, dict)
    ]


class TestEventTypes:
    def test_expected_event_types_frozen(self) -> None:
        assert CAPABILITY_REGISTRY_EVENT_TYPES == frozenset(
            {
                "capability_registry_loaded",
                "capability_registry_validation_passed",
                "capability_registry_validation_failed",
                "capability_registry_capability_viewed",
                "capability_registry_capability_blocked",
                "capability_registry_permission_classified",
                "capability_registry_trust_classified",
                "capability_registry_manifest_rejected",
                "capability_registry_route_governance_checked",
                "capability_registry_no_dynamic_loading_checked",
            }
        )

    def test_safe_payload_fields_excludes_secrets(self) -> None:
        for forbidden in ("apiKey", "Authorization", "secret", "tokenHash"):
            assert forbidden not in SAFE_PAYLOAD_FIELDS


class TestPayloadRedaction:
    def test_only_safe_fields_kept(self) -> None:
        payload = {
            "capabilityId": "tool.read.x",
            "status": "enabled",
            "apiKey": "sk-leak-1234567890",
            "Authorization": "Bearer abc",
            "shellCommand": "rm -rf /",
            "secret": "topsecret",
            "rawPrompt": "tell me the key",
        }
        cleaned = redact_capability_registry_payload(payload)
        for forbidden in ("apiKey", "Authorization", "shellCommand", "secret", "rawPrompt"):
            assert forbidden not in cleaned
        assert cleaned["capabilityId"] == "tool.read.x"
        assert cleaned["status"] == "enabled"
        assert cleaned["redactionApplied"] is True

    def test_non_json_values_dropped(self) -> None:
        cleaned = redact_capability_registry_payload(
            {"capabilityId": "x.y", "safeMetadata": b"bytes-leak"}
        )
        # bytes value must never be stringified into the payload.
        blob = json.dumps(cleaned)
        assert "bytes-leak" not in blob

    def test_non_mapping_returns_empty(self) -> None:
        assert redact_capability_registry_payload(None) == {}
        assert redact_capability_registry_payload("string") == {}


class TestWrite:
    def test_write_emits_under_dev_home(self, tmp_path: Path) -> None:
        home = tmp_path / "dev-home"
        home.mkdir()
        result = write_capability_registry_audit(
            event_type="capability_registry_loaded",
            capability_id="registry.capability_registry_status",
            category="registry",
            permission_class="READ_ONLY",
            trust_level="BUILTIN_VERIFIED",
            status="enabled",
            hermes_home=str(home),
        )
        assert result.written is True
        assert result.event_id

        events = list(_events(home))
        assert any(
            e.get("eventType") == "capability_registry_loaded"
            and e.get("source") == CAPABILITY_REGISTRY_AUDIT_SOURCE
            for e in events
        )

    def test_unknown_event_type_normalized(self, tmp_path: Path) -> None:
        home = tmp_path / "dev-home"
        home.mkdir()
        result = write_capability_registry_audit(
            event_type="capability_registry_evil_unknown",
            hermes_home=str(home),
        )
        assert result.written is True
        events = _events(home)
        assert events[-1]["eventType"] == "capability_registry_loaded"

    def test_forbidden_field_never_persisted(self, tmp_path: Path) -> None:
        home = tmp_path / "dev-home"
        home.mkdir()
        # Caller tries to smuggle a secret via the safe_metadata mapping.
        write_capability_registry_audit(
            event_type="capability_registry_capability_viewed",
            capability_id="provider.live_manual_one_shot",
            safe_metadata={"apiKey": "sk-leak-1234567890", "Authorization": "Bearer xyz"},
            hermes_home=str(home),
        )
        blob = json.dumps(_events(home))
        for token in _FORBIDDEN_TOKENS:
            assert token not in blob, f"forbidden token {token!r} persisted in audit"

    def test_write_never_raises_on_bad_home(self) -> None:
        # A bogus HERMES_HOME must not raise; audit failure never enables a capability.
        result = write_capability_registry_audit(
            event_type="capability_registry_loaded",
            hermes_home="/nonexistent/path/that/does/not/exist/xyz",
        )
        assert result.written is False
        assert result.error_code

    def test_audit_source_is_internal_kind(self, tmp_path: Path) -> None:
        home = tmp_path / "dev-home"
        home.mkdir()
        write_capability_registry_audit(
            event_type="capability_registry_route_governance_checked",
            hermes_home=str(home),
        )
        events = _events(home)
        ev = events[-1]
        # Reuses AUDIT_KIND_INTERNAL — no new audit kind introduced.
        assert ev["auditKind"] == "internal"
        assert ev["redactionApplied"] is True


class TestNoProductionHome:
    def test_write_refuses_production_home(self) -> None:
        # The store root guard refuses anything under ~/.hermes / production.
        result = write_capability_registry_audit(
            event_type="capability_registry_loaded",
            hermes_home="/Users/huangruibang/.hermes",
        )
        assert result.written is False
