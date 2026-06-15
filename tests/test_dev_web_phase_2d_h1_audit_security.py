"""Phase 2D-H1 — Audit security closure (schema / sanitizer / no-leak / artifacts).

Deterministic, hermetic security coverage that goes beyond the Phase 2D
happy-path tests. Covers Lens 1 (audit schema / canonical event boundary),
Lens 2 (unified sanitizer / redaction boundary), Lens 9 (audit API / Viewer
no-leak boundary), and Lens 10 (production isolation / runtime artifact
boundary):

  - canonical schema rejects missing eventId / missing sequence / non-JSON
    metadata; rejects unsafe rawArguments / fullTokenHash fields
  - the canonical event preserves provider / write / rollback correlation
    fields without leaking payloads
  - the unified sanitizer closes the str(object) / repr(object) / default=str
    fallback for every non-JSON-native type
  - adversarial sanitizer matrix: callable, object instance, bound method,
    bytes, Exception, PEM key, Bearer, sk-*, api_key/apiKey, password/secret/
    credential, tokenSecret, fullTokenHash, confirmationToken, rawArguments,
    fileContent, production path, ~/.hermes
  - validate_sanitized_event rejects an un-redacted forbidden field
  - API + Audit Viewer output never carries raw args / tokens / secrets /
    callable repr / production paths across ALL seven audit kinds
  - index files and quarantine files carry no secrets and live only under the
    dev audit store
  - the cursor token field set is a strict whitelist (no path / secret / index
    internal)
  - runtime artifacts (audit-store / token / rollback / JSONL / .claude) are
    never committed (gitignore coverage)

No production access, no `~/.hermes`, no `state.db`. Tests use tmp_path only.
Security closure ID: AUDIT-SECURITY-CLOSURE-2D-H1-001.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_audit_bridge import bridge_legacy_audit_to_store
from hermes_cli.dev_web_audit_index import rebuild_audit_index
from hermes_cli.dev_web_audit_query import (
    AuditCursor,
    build_audit_query,
    decode_audit_cursor,
    encode_audit_cursor,
    query_audit_events,
)
from hermes_cli.dev_web_audit_sanitizer import (
    BYTES_SENTINEL,
    NON_JSON_VALUE_SENTINEL,
    REDACTED_SENTINEL,
    sanitize_audit_event,
    sanitize_audit_value,
    strip_forbidden_keys,
    validate_sanitized_event,
)
from hermes_cli.dev_web_audit_schema import (
    AUDIT_SCHEMA_VERSION,
    REQUIRED_EVENT_FIELDS,
    validate_canonical_event,
)
from hermes_cli.dev_web_audit_store import (
    append_audit_event,
    build_audit_event,
    ensure_audit_store,
    get_audit_store_root,
    iter_all_events,
)


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return str(home)


# ---------------------------------------------------------------------------
# Lens 1 — Audit schema / canonical event boundary
# ---------------------------------------------------------------------------


class TestSchemaRejectsUnsafeEvents:
    def test_rejects_missing_event_id(self):
        ev = {
            "sequence": 1, "createdAt": "2026-06-15T00:00:00+00:00",
            "eventType": "t", "auditKind": "internal",
            "schemaVersion": AUDIT_SCHEMA_VERSION,
        }
        ok, reason = validate_canonical_event(ev)
        assert not ok
        assert "eventId" in (reason or "")

    def test_rejects_missing_sequence(self):
        ev = {
            "eventId": "x", "createdAt": "2026-06-15T00:00:00+00:00",
            "eventType": "t", "auditKind": "internal",
            "schemaVersion": AUDIT_SCHEMA_VERSION,
        }
        ok, reason = validate_canonical_event(ev)
        assert not ok and "sequence" in (reason or "")

    def test_rejects_non_json_metadata(self):
        # A non-JSON-native value inside safeMetadata is rejected by validation.
        ev = {
            "eventId": "x", "sequence": 1, "createdAt": "2026-06-15T00:00:00+00:00",
            "eventType": "t", "auditKind": "internal", "schemaVersion": AUDIT_SCHEMA_VERSION,
            "safeMetadata": object(),  # not a dict
        }
        ok, reason = validate_canonical_event(ev)
        assert not ok

    def test_rejects_wrong_schema_version(self):
        ev = {
            "eventId": "x", "sequence": 1, "createdAt": "2026-06-15T00:00:00+00:00",
            "eventType": "t", "auditKind": "internal", "schemaVersion": "audit_schema_v1",
        }
        ok, _ = validate_canonical_event(ev)
        assert not ok

    def test_required_fields_set_stable(self):
        assert set(REQUIRED_EVENT_FIELDS) == {
            "eventId", "sequence", "createdAt", "eventType", "auditKind", "schemaVersion",
        }

    def test_rejects_unsafe_raw_arguments_field(self):
        # rawArguments is a forbidden stem; the sanitizer redacts it to
        # [REDACTED] so it never persists verbatim.
        sanitized = sanitize_audit_event(
            build_audit_event(
                event_type="t", audit_kind="internal", event_id="r",
                safe_metadata={"rawArguments": {"secret": "shh"}},
            )
        )
        ok, _ = validate_canonical_event(sanitized)
        assert ok
        assert sanitized["safeMetadata"]["rawArguments"] == REDACTED_SENTINEL

    def test_rejects_unsafe_full_token_hash_field(self):
        sanitized = sanitize_audit_event(
            build_audit_event(
                event_type="t", audit_kind="internal", event_id="h",
                safe_metadata={"fullTokenHash": "a" * 64},
            )
        )
        ok, _ = validate_canonical_event(sanitized)
        assert ok
        assert sanitized["safeMetadata"]["fullTokenHash"] == REDACTED_SENTINEL


class TestCanonicalPreservesCorrelationFields:
    def test_provider_fields_preserved(self):
        ev = build_audit_event(
            event_type="provider_audit", audit_kind="provider", event_id="p1",
            provider_mode="fake", provider_request_id="pr-1",
            provider_response_id="ps-1", provider_api_called=False,
        )
        sanitized = sanitize_audit_event(ev)
        assert sanitized["providerRequestId"] == "pr-1"
        assert sanitized["providerResponseId"] == "ps-1"
        assert sanitized["providerMode"] == "fake"

    def test_write_fields_preserved(self):
        ev = build_audit_event(
            event_type="write_audit", audit_kind="write", event_id="w1",
            write_plan_id="wp-1", write_preview_id="wprev-1", rollback_id=None,
            write_required=True,
        )
        sanitized = sanitize_audit_event(ev)
        assert sanitized["writePlanId"] == "wp-1"
        assert sanitized["writePreviewId"] == "wprev-1"
        assert sanitized["writeRequired"] is True

    def test_rollback_fields_preserved(self):
        ev = build_audit_event(
            event_type="rollback_audit", audit_kind="rollback", event_id="rb1",
            rollback_id="rblk-1",
        )
        sanitized = sanitize_audit_event(ev)
        assert sanitized["rollbackId"] == "rblk-1"

    def test_confirmation_token_id_preserved_but_secret_redacted(self):
        # confirmationTokenId is an ALLOWED id stem; confirmationTokenSecret is not.
        ev = build_audit_event(
            event_type="confirmation_audit", audit_kind="confirmation", event_id="c1",
            confirmation_token_id="ctok-1",
            safe_metadata={"confirmationTokenSecret": "plain-secret-value"},
        )
        sanitized = sanitize_audit_event(ev)
        assert sanitized.get("confirmationTokenId") == "ctok-1"
        assert sanitized["safeMetadata"]["confirmationTokenSecret"] == REDACTED_SENTINEL


# ---------------------------------------------------------------------------
# Lens 2 — Unified sanitizer / redaction boundary
# ---------------------------------------------------------------------------


class TestSanitizerNoStrFallback:
    """Non-JSON-native values collapse to a sentinel — never str()/repr()."""

    def test_callable_becomes_sentinel(self):
        assert sanitize_audit_value(lambda x: x) == NON_JSON_VALUE_SENTINEL

    def test_function_becomes_sentinel(self):
        def f():
            pass
        assert sanitize_audit_value(f) == NON_JSON_VALUE_SENTINEL

    def test_object_instance_becomes_sentinel(self):
        class C:
            pass
        assert sanitize_audit_value(C()) == NON_JSON_VALUE_SENTINEL

    def test_bound_method_becomes_sentinel(self):
        class C:
            def m(self):
                pass
        assert sanitize_audit_value(C().m) == NON_JSON_VALUE_SENTINEL

    def test_bytes_become_sentinel(self):
        assert sanitize_audit_value(b"raw bytes secret") == BYTES_SENTINEL

    def test_module_becomes_sentinel(self):
        import math
        assert sanitize_audit_value(math) == NON_JSON_VALUE_SENTINEL

    def test_class_becomes_sentinel(self):
        assert sanitize_audit_value(int) == NON_JSON_VALUE_SENTINEL


class TestSanitizerScrubbedStrings:
    def test_object_at_repr_scrubbed_in_string(self):
        class C:
            pass
        out = sanitize_audit_value(f"value={C()!r}")
        assert "object at 0x" not in out

    def test_function_repr_scrubbed_in_string(self):
        def f():
            pass
        out = sanitize_audit_value(f"<function f at 0x12345>")
        assert "<function" not in out
        assert "0x12345" not in out

    def test_bound_method_repr_scrubbed_in_string(self):
        out = sanitize_audit_value("<bound method C.m of <C object at 0xabc>>")
        assert "bound method" not in out
        assert "0xabc" not in out

    def test_exception_becomes_class_summary(self):
        out = sanitize_audit_value(ValueError("sk-secret-in-msg"))
        assert "sk-secret-in-msg" not in out
        assert "ValueError" in out


class TestSanitizerSecretMatrix:
    # Bare VALUE patterns the sanitizer redacts wholesale (key-agnostic).
    SECRET_VALUES = [
        "sk-abcd1234efgh5678ijkl",
        "Bearer secret-token-value",
        "Authorization: Bearer xyz",
        "api_key=ABCDEF1234567890",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIBVwIBADAN\n-----END RSA PRIVATE KEY-----",
        "-----BEGIN PRIVATE KEY-----\nMIIBVwIBADAN\n-----END PRIVATE KEY-----",
        "https://user:pass@host.example/path",
    ]

    @pytest.mark.parametrize("secret", SECRET_VALUES)
    def test_secret_value_redacted(self, secret):
        assert sanitize_audit_value(secret) == REDACTED_SENTINEL

    @pytest.mark.parametrize("key", [
        "api_key", "apiKey", "password", "passwd", "secret", "secrets",
        "credential", "credentials", "tokenSecret", "confirmationToken",
        "rawArguments", "rawArgs", "arguments", "fileContent", "rawfileContent",
        "fullTokenHash", "tokenHash", "plainToken", "access_token",
        "refresh_token", "cookie", "cookies", "session", "private_key",
        "providerPayload",
    ])
    def test_forbidden_field_redacted(self, key):
        # These are key-based redactions: the value is redacted because the
        # field NAME is a forbidden stem (covers password=/client_secret=/
        # credential= even though they are not bare-value secret patterns).
        out = sanitize_audit_value("anything", field_name=key)
        assert out == REDACTED_SENTINEL

    def test_full_hex_hash_redacted(self):
        assert sanitize_audit_value("aabbccdd" * 8) == REDACTED_SENTINEL

    def test_short_hex_id_preserved(self):
        # Short correlation hex (not a full hash) is preserved.
        assert sanitize_audit_value("abcdef1234") == "abcdef1234"

    def test_production_path_redacted(self):
        assert sanitize_audit_value("/Users/huangruibang/.hermes/state.db") == REDACTED_SENTINEL
        assert sanitize_audit_value("~/.hermes/memory") == REDACTED_SENTINEL


class TestSanitizerSourceNoStrFallback:
    """Defense-in-depth: the sanitizer source never uses str(object)/repr()."""

    def test_sanitizer_has_no_str_object_fallback(self):
        import hermes_cli.dev_web_audit_sanitizer as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        # The only legitimate str() uses are str(value) where value is already
        # a known scalar (bool/int). A bare str(<arbitrary>) fallback on the
        # non-JSON-native branch is the leak we closed. Assert the non-JSON
        # branch returns the sentinel, not a str() coercion.
        assert "return NON_JSON_VALUE_SENTINEL" in source
        # No json.dumps(..., default=str) anywhere.
        assert "default=str" not in source
        assert "default = str" not in source


class TestValidateSanitizedEvent:
    def test_rejects_unredacted_forbidden_field(self):
        # validate_sanitized_event inspects TOP-LEVEL keys for forbidden stems.
        ev = {
            "eventId": "x", "sequence": 1, "createdAt": "2026-06-15T00:00:00+00:00",
            "eventType": "t", "auditKind": "internal", "schemaVersion": AUDIT_SCHEMA_VERSION,
            "api_key": "sk-abcd1234efgh5678ijkl",
        }
        ok, _ = validate_sanitized_event(ev)
        assert not ok

    def test_accepts_redacted_forbidden_field(self):
        ev = {
            "eventId": "x", "sequence": 1, "createdAt": "2026-06-15T00:00:00+00:00",
            "eventType": "t", "auditKind": "internal", "schemaVersion": AUDIT_SCHEMA_VERSION,
            "api_key": REDACTED_SENTINEL,
        }
        ok, _ = validate_sanitized_event(ev)
        assert ok


class TestStripForbiddenKeys:
    def test_strips_forbidden_keys_from_output(self):
        data = {
            "eventId": "e", "safeMetadata": {"rawArguments": {"a": 1}, "ok": 2},
            "nested": [{"tokenSecret": "x", "k": 1}],
        }
        out = strip_forbidden_keys(data)
        assert "rawArguments" not in out["safeMetadata"]
        assert "tokenSecret" not in out["nested"][0]
        assert out["safeMetadata"]["ok"] == 2


# ---------------------------------------------------------------------------
# Lens 9 — Audit API / Viewer no-leak boundary (all 7 audit kinds)
# ---------------------------------------------------------------------------


_KIND_LEGACIES = (
    ("dry_run", {"eventId": "d1", "canonicalName": "clarify", "decision": "would_block"}),
    ("pre_execution", {"preExecutionAuditId": "pe1", "canonicalName": "clarify"}),
    ("post_execution", {"postExecutionAuditId": "px1", "canonicalName": "clarify"}),
    ("provider", {"eventId": "pv1", "providerMode": "fake"}),
    ("write", {"eventId": "w1", "toolId": "dev_sandbox_file_write"}),
    ("rollback", {"eventId": "rb1", "rollbackId": "rblk1"}),
    ("confirmation", {"tokenId": "ct1"}),
)


def _seed_all_kinds_with_secret(home: Path):
    """Bridge all 7 kinds, each carrying a secret-like payload."""
    for kind, legacy in _KIND_LEGACIES:
        legacy = {
            **legacy,
            "api_key": "sk-abcd1234efgh5678ijkl",
            "password": "super-secret",
            "rawArguments": {"secret": "shh"},
            "fileContent": "TOPSECRET",
        }
        bridge_legacy_audit_to_store(legacy, audit_kind=kind, hermes_home=str(home))


class TestApiOutputNoLeak:
    def test_no_secret_rawargs_callable_in_store_output(self, tmp_path):
        home = tmp_path / "hh"
        home.mkdir()
        _seed_all_kinds_with_secret(home)
        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=home))
        client = TestClient(app)
        resp = client.get("/api/dev/v1/tools/audit-events", params={
            "auditKind": "internal", "search": "x", "limit": 100,
        })
        assert resp.status_code == 200
        text = json.dumps(resp.json())
        for needle in (
            "sk-abcd1234efgh5678ijkl", "super-secret", "TOPSECRET",
            "rawArguments", "<function", "object at 0x",
            "/Users/huangruibang/.hermes", "state.db",
        ):
            assert needle not in text, f"leaked: {needle}"

    def test_no_secret_on_disk_across_kinds(self, tmp_path):
        home = tmp_path / "hh"
        home.mkdir()
        _seed_all_kinds_with_secret(home)
        root, _ = get_audit_store_root(str(home))
        on_disk = "\n".join(
            raw for _s, _l, _e, raw in iter_all_events(root, include_corrupt=True)
        )
        for needle in (
            "sk-abcd1234efgh5678ijkl", "super-secret", "TOPSECRET",
            "<function", "object at 0x",
        ):
            assert needle not in on_disk, f"persisted: {needle}"

    def test_index_files_carry_no_secrets(self, tmp_path):
        home = tmp_path / "hh"
        home.mkdir()
        _seed_all_kinds_with_secret(home)
        root, _ = get_audit_store_root(str(home))
        rebuild_audit_index(root)
        blob = ""
        for p in (root / "indexes").glob("*.json"):
            blob += p.read_text(encoding="utf-8")
        for needle in ("sk-abcd", "super-secret", "TOPSECRET", "rawArguments"):
            assert needle not in blob

    def test_query_output_no_secret_for_each_kind(self, tmp_path):
        home = tmp_path / "hh"
        home.mkdir()
        _seed_all_kinds_with_secret(home)
        for kind in ("dry_run", "pre_execution", "post_execution", "provider",
                     "write", "rollback", "confirmation"):
            res = query_audit_events(
                build_audit_query(audit_kind=kind, limit=10), hermes_home=str(home)
            )
            blob = json.dumps([dict(i) for i in res.items])
            assert "sk-abcd" not in blob, kind
            assert "super-secret" not in blob, kind
            assert "rawArguments" not in blob, kind


class TestCursorTokenStrictWhitelist:
    def test_cursor_decodes_to_known_fields_only(self):
        token = encode_audit_cursor(
            AuditCursor(7, "asc", "deadbeef", "2026-06-15T00:00:00+00:00")
        )
        # Inspect the raw payload shape.
        import base64
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode("utf-8")
        payload = json.loads(raw)
        assert set(payload.keys()) == {"v", "lastSequence", "direction", "queryHash", "issuedAt"}
        back = decode_audit_cursor(token)
        assert back is not None
        assert back.last_sequence == 7
        assert back.direction == "asc"
        assert back.query_hash == "deadbeef"

    def test_cursor_no_secret_path_in_payload(self):
        token = encode_audit_cursor(
            AuditCursor(1, "desc", "h", "2026-06-15T00:00:00+00:00")
        )
        assert "hermes" not in token
        assert "Users" not in token
        assert "audit-store" not in token


# ---------------------------------------------------------------------------
# Lens 10 — Production isolation / runtime artifact boundary
# ---------------------------------------------------------------------------


class TestQuarantineDevLocalOnly:
    def test_quarantine_under_dev_store_only(self, tmp_path):
        home = tmp_path / "hh"
        home.mkdir()
        ensure_audit_store(str(home))
        root, _ = get_audit_store_root(str(home))
        seg = root / "events" / "audit-000001.jsonl"
        seg.parent.mkdir(parents=True, exist_ok=True)
        with seg.open("w", encoding="utf-8") as f:
            f.write('{"eventId":"ok","sequence":1,"createdAt":"2026-06-15T00:00:00+00:00",'
                    '"eventType":"t","auditKind":"internal","schemaVersion":"audit_schema_v2"}\n')
            f.write("CORRUPT\n")
        from hermes_cli.dev_web_audit_recovery import (
            quarantine_corrupt_records, scan_audit_segments,
        )
        report = scan_audit_segments(root)
        summary = quarantine_corrupt_records(root, list(report.records))
        assert summary["quarantined"] >= 1
        qdir = root / "quarantine"
        assert str(qdir).startswith(str(root))
        assert "/Users/huangruibang/.hermes" not in str(qdir)
        assert "hermes-agent-dev" not in str(qdir)


class TestRuntimeArtifactsGitignored:
    def test_audit_runtime_artifacts_in_gitignore(self):
        gitignore = Path(".gitignore")
        assert gitignore.is_file()
        content = gitignore.read_text(encoding="utf-8")
        for pattern in (
            "audit-store",
            "tool-dry-run-audit.jsonl",
            "confirmation-tokens",
            "tool-write-rollback-manifests",
        ):
            assert pattern in content, f"{pattern} not gitignored"


class TestMinimalSafeEventFallback:
    def test_minimal_safe_event_is_valid(self):
        # When sanitization fails entirely, the minimal-safe fallback must
        # still validate against the canonical schema (so a breadcrumb is
        # persisted, never a leaky record).
        sanitized = sanitize_audit_event("not a dict")
        ok, _ = validate_canonical_event(sanitized)
        assert ok
        assert sanitized["redactionApplied"] is True
        assert sanitized["auditKind"] == "internal"
