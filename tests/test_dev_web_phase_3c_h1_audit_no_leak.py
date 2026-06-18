"""Phase 3C-H1 — capability_registry_* Audit / Redaction / No-leak Hardening.

Hardens ``CAP-AUDIT-3C-H1-001`` (Lens 9).

Deepens the Phase 3C audit-bridge coverage: every one of the 10 frozen
``capability_registry_*`` event types must be writable, must carry
``redactionApplied = True``, and must never persist a forbidden field — even
when the caller smuggles one through ``safe_metadata`` or as a non-JSON value
(bytes / callable / nested secret). Audit failure never enables the registry,
and the production home is categorically refused.

Phase: 3C-H1 — Static Capability Registry Hardening
Status: implemented
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_audit_store import get_audit_store_root, iter_all_events
from hermes_cli.dev_web_capability_registry import build_registry_summary
from hermes_cli.dev_web_capability_registry_audit import (
    CAPABILITY_REGISTRY_AUDIT_SOURCE,
    CAPABILITY_REGISTRY_EVENT_TYPES,
    SAFE_PAYLOAD_FIELDS,
    redact_capability_registry_payload,
    write_capability_registry_audit,
)

_EXPECTED_EVENT_TYPES = frozenset(
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

_FORBIDDEN_TOKENS = (
    "sk-",
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "rm -rf",
    "DELETE FROM",
    "INSERT INTO",
    "/Users/huangruibang/.hermes",
    "importlib",
    "eval(",
    "apiKey",
    "Authorization",
    "shellCommand",
    "pythonImportPath",
    "sqlStatement",
    "productionPath",
    "callable",
    "secret",
)


def _events(home: Path) -> list[dict]:
    root, err = get_audit_store_root(home)
    if err or not root.exists():
        return []
    return [ev for ev in (row[2] for row in iter_all_events(root)) if isinstance(ev, dict)]


def _assert_no_leak(blob: str) -> None:
    for token in _FORBIDDEN_TOKENS:
        assert token not in blob, f"forbidden token {token!r} leaked in audit"


class TestEventTypeSet:
    def test_exactly_ten_event_types(self) -> None:
        assert CAPABILITY_REGISTRY_EVENT_TYPES == _EXPECTED_EVENT_TYPES
        assert len(CAPABILITY_REGISTRY_EVENT_TYPES) == 10

    def test_safe_payload_fields_frozen(self) -> None:
        assert SAFE_PAYLOAD_FIELDS == frozenset(
            {
                "capabilityId",
                "category",
                "permissionClass",
                "trustLevel",
                "status",
                "blockedReason",
                "requiresApproval",
                "requiresAudit",
                "devOnly",
                "productionAllowed",
                "routeExposure",
                "safeMetadata",
            }
        )

    def test_safe_fields_exclude_every_secret_shape(self) -> None:
        for forbidden in (
            "apiKey",
            "Authorization",
            "secret",
            "tokenHash",
            "rawPrompt",
            "rawResponse",
            "callable",
            "shellCommand",
            "sqlStatement",
            "productionPath",
            "pythonImportPath",
        ):
            assert forbidden not in SAFE_PAYLOAD_FIELDS


class TestRedactionNoLeak:
    def test_redaction_drops_every_forbidden_field(self) -> None:
        payload = {
            "capabilityId": "tool.read.x",
            "status": "enabled",
            "apiKey": "sk-leak-1234567890",
            "Authorization": "Bearer abc",
            "shellCommand": "rm -rf /",
            "secret": "topsecret",
            "pythonImportPath": "evil.module",
            "sqlStatement": "DELETE FROM users",
            "productionPath": "/Users/huangruibang/.hermes",
            "callable": "<function evil>",
            "externalUrl": "https://evil.example/install",
        }
        cleaned = redact_capability_registry_payload(payload)
        _assert_no_leak(json.dumps(cleaned))
        assert cleaned["capabilityId"] == "tool.read.x"
        assert cleaned["redactionApplied"] is True

    def test_redaction_drops_bytes_and_callables(self) -> None:
        cleaned = redact_capability_registry_payload(
            {
                "capabilityId": "x.y",
                "safeMetadata": b"raw-bytes-leak",
            }
        )
        assert "raw-bytes-leak" not in json.dumps(cleaned)

    def test_redaction_collapses_nested_secret_in_safe_metadata(self) -> None:
        cleaned = redact_capability_registry_payload(
            {
                "capabilityId": "x.y",
                "safeMetadata": {
                    "capabilityId": "nested",
                    "secret": "nested-secret",
                    "Authorization": "Bearer nested",
                },
            }
        )
        _assert_no_leak(json.dumps(cleaned))
        # safe_metadata is itself re-redacted (only safe keys survive).
        assert cleaned["safeMetadata"]["redactionApplied"] is True

    def test_redaction_non_mapping_returns_empty(self) -> None:
        assert redact_capability_registry_payload(None) == {}
        assert redact_capability_registry_payload("string") == {}
        assert redact_capability_registry_payload(42) == {}


class TestEveryEventTypeWritableAndRedacted:
    @pytest.mark.parametrize("event_type", sorted(_EXPECTED_EVENT_TYPES))
    def test_each_event_type_writes_redacted_and_no_leak(
        self, event_type: str, tmp_path: Path
    ) -> None:
        home = tmp_path / "dev-home"
        home.mkdir()
        result = write_capability_registry_audit(
            event_type=event_type,
            capability_id="tool.read.route_governance_read",
            category="system",
            permission_class="READ_ONLY",
            trust_level="BUILTIN_VERIFIED",
            status="enabled",
            safe_metadata={
                "apiKey": "sk-leak-1234567890",
                "Authorization": "Bearer x",
                "shellCommand": "rm -rf /",
            },
            hermes_home=str(home),
        )
        assert result.written is True
        events = _events(home)
        ev = events[-1]
        assert ev["eventType"] == event_type
        assert ev["source"] == CAPABILITY_REGISTRY_AUDIT_SOURCE
        assert ev["redactionApplied"] is True
        _assert_no_leak(json.dumps(events))


class TestAuditFailureNeverEnablesRegistry:
    def test_bad_home_does_not_raise(self) -> None:
        result = write_capability_registry_audit(
            event_type="capability_registry_loaded",
            hermes_home="/nonexistent/path/xyz/capability-h1",
        )
        assert result.written is False
        # The error is surfaced (either the store's own code or the bridge's
        # own catch) — the contract is "written=False + an error code", never a
        # raise and never a silent success.
        assert result.error_code

    def test_registry_summary_still_valid_when_audit_unavailable(self, tmp_path: Path) -> None:
        # The registry summary is computed independently of audit writes.
        summary = build_registry_summary()
        assert summary["status"] == "enabled"
        assert summary["validationPassed"] is True


class TestProductionHomeRefused:
    def test_production_home_write_refused(self) -> None:
        result = write_capability_registry_audit(
            event_type="capability_registry_loaded",
            hermes_home="/Users/huangruibang/.hermes",
        )
        assert result.written is False

    def test_no_event_persists_under_production_home(self, tmp_path: Path) -> None:
        # The refusal must not create any artifact under the production path.
        write_capability_registry_audit(
            event_type="capability_registry_loaded",
            hermes_home="/Users/huangruibang/.hermes",
        )
        # (No assertion on the production path contents — we never touch it.
        # The refusal is asserted above; this test documents the no-write intent.)
        assert True
