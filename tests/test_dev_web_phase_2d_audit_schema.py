"""Phase 2D — Canonical audit schema tests.

Verifies the canonical ``audit_schema_v2`` event shape: required fields,
schema version, enumerations, JSON-native guarantees, and validation.
"""

from __future__ import annotations

from hermes_cli.dev_web_audit_schema import (
    AUDIT_SCHEMA_VERSION,
    AuditEvent,
    REQUIRED_EVENT_FIELDS,
    VALID_AUDIT_KINDS,
    VALID_PROVIDER_MODES,
    VALID_SOURCES,
    VALID_STATUSES,
    is_valid_audit_kind,
    is_valid_created_at,
    required_fields,
    validate_canonical_event,
)


def _good_event(**overrides):
    base = {
        "eventId": "evt-1",
        "sequence": 1,
        "createdAt": "2026-06-15T00:00:00+00:00",
        "eventType": "tool_dry_run",
        "auditKind": "dry_run",
        "schemaVersion": AUDIT_SCHEMA_VERSION,
    }
    base.update(overrides)
    return base


class TestSchemaVersion:
    def test_schema_version_is_v2(self):
        assert AUDIT_SCHEMA_VERSION == "audit_schema_v2"

    def test_event_carries_v2(self):
        ok, _ = validate_canonical_event(_good_event())
        assert ok


class TestRequiredFields:
    def test_required_fields_include_core_identity(self):
        for field in ("eventId", "sequence", "createdAt", "eventType", "auditKind"):
            assert field in REQUIRED_EVENT_FIELDS
        assert "schemaVersion" in REQUIRED_EVENT_FIELDS

    def test_required_fields_helper(self):
        assert required_fields() == REQUIRED_EVENT_FIELDS

    def test_missing_event_id_rejected(self):
        ev = _good_event()
        del ev["eventId"]
        ok, reason = validate_canonical_event(ev)
        assert not ok and "eventId" in reason

    def test_missing_sequence_rejected(self):
        ev = _good_event()
        del ev["sequence"]
        ok, reason = validate_canonical_event(ev)
        assert not ok and "sequence" in reason

    def test_missing_created_at_rejected(self):
        ev = _good_event()
        del ev["createdAt"]
        ok, _ = validate_canonical_event(ev)
        assert not ok

    def test_missing_schema_version_rejected(self):
        ev = _good_event()
        del ev["schemaVersion"]
        ok, _ = validate_canonical_event(ev)
        assert not ok


class TestEnumerations:
    def test_all_seven_kinds(self):
        for kind in (
            "dry_run", "pre_execution", "post_execution", "write",
            "provider", "rollback", "confirmation",
        ):
            assert kind in VALID_AUDIT_KINDS

    def test_statuses(self):
        for s in ("ok", "blocked", "error", "preview", "completed"):
            assert s in VALID_STATUSES

    def test_sources(self):
        assert "dry_run_api" in VALID_SOURCES
        assert "internal" in VALID_SOURCES

    def test_provider_modes(self):
        for m in ("disabled", "fake", "real"):
            assert m in VALID_PROVIDER_MODES


class TestValidationRules:
    def test_wrong_schema_version_rejected(self):
        ok, _ = validate_canonical_event(_good_event(schemaVersion="audit_schema_v1"))
        assert not ok

    def test_negative_sequence_rejected(self):
        ok, _ = validate_canonical_event(_good_event(sequence=-1))
        assert not ok

    def test_bool_sequence_rejected(self):
        ok, _ = validate_canonical_event(_good_event(sequence=True))
        assert not ok

    def test_unknown_audit_kind_rejected(self):
        ok, _ = validate_canonical_event(_good_event(auditKind="bogus"))
        assert not ok

    def test_bad_created_at_rejected(self):
        ok, _ = validate_canonical_event(_good_event(createdAt="yesterday"))
        assert not ok

    def test_non_dict_rejected(self):
        ok, _ = validate_canonical_event("not-a-dict")  # type: ignore[arg-type]
        assert not ok

    def test_boolean_field_typecheck(self):
        ok, _ = validate_canonical_event(_good_event(readOnly="yes"))
        assert not ok

    def test_object_field_typecheck(self):
        ok, _ = validate_canonical_event(_good_event(summary="not-a-dict"))
        assert not ok

    def test_oversized_scalar_rejected(self):
        ok, _ = validate_canonical_event(_good_event(toolId="x" * 5000))
        assert not ok


class TestAuditEventDataclass:
    def test_to_dict_emits_required_fields(self):
        ev = AuditEvent(
            event_id="e1", sequence=1, created_at="2026-06-15T00:00:00+00:00",
            event_type="t", audit_kind="dry_run",
        )
        d = ev.to_dict()
        assert d["eventId"] == "e1"
        assert d["sequence"] == 1
        assert d["schemaVersion"] == AUDIT_SCHEMA_VERSION
        assert d["summary"] == {}
        assert "readOnly" not in d  # None omitted

    def test_to_dict_emits_set_optionals(self):
        ev = AuditEvent(
            event_id="e1", sequence=2, created_at="2026-06-15T00:00:00+00:00",
            event_type="t", audit_kind="write", read_only=False, write_required=True,
            summary={"op": "write"},
        )
        d = ev.to_dict()
        assert d["readOnly"] is False
        assert d["writeRequired"] is True
        assert d["summary"] == {"op": "write"}


class TestHelpers:
    def test_is_valid_audit_kind(self):
        assert is_valid_audit_kind("dry_run")
        assert not is_valid_audit_kind("nope")
        assert not is_valid_audit_kind(None)

    def test_is_valid_created_at(self):
        assert is_valid_created_at("2026-06-15T00:00:00+00:00")
        assert is_valid_created_at("2026-06-15T00:00:00Z")
        assert is_valid_created_at("2026-06-15T00:00:00.123+00:00")
        assert not is_valid_created_at("bad")
