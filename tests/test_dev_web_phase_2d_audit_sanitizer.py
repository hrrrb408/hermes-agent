"""Phase 2D — Unified audit sanitizer tests.

Verifies the unified sanitizer redacts secrets, callable/function/object reprs,
bytes, raw arguments, full token hashes, production paths, and PEM blocks —
and that the Phase 2A ``str(value)`` fallback gap is closed (non-JSON-native
values collapse to ``<non_json_value>`` rather than a repr).
"""

from __future__ import annotations

import json

from hermes_cli.dev_web_audit_sanitizer import (
    BYTES_SENTINEL,
    NON_JSON_VALUE_SENTINEL,
    REDACTED_SENTINEL,
    redact_callable_repr,
    redact_path_like_string,
    redact_secret_like_string,
    redact_token_like_string,
    sanitize_audit_event,
    sanitize_audit_metadata,
    sanitize_audit_value,
    validate_sanitized_event,
)


class TestNonJsonNativeFallback:
    """The Phase 2A str(value) gap is closed."""

    def test_callable_returns_sentinel(self):
        assert sanitize_audit_value(lambda: 1) == NON_JSON_VALUE_SENTINEL

    def test_function_object_returns_sentinel(self):
        def f():
            pass

        assert sanitize_audit_value(f) == NON_JSON_VALUE_SENTINEL

    def test_arbitrary_object_returns_sentinel(self):
        class Foo:
            pass

        assert sanitize_audit_value(Foo()) == NON_JSON_VALUE_SENTINEL

    def test_object_repr_not_leaked_in_string(self):
        class Foo:
            pass

        result = sanitize_audit_value(f"got {Foo()!r} here")
        assert "object at 0x" not in result

    def test_module_returns_sentinel(self):
        import sys

        assert sanitize_audit_value(sys) == NON_JSON_VALUE_SENTINEL

    def test_class_returns_sentinel(self):
        assert sanitize_audit_value(int) == NON_JSON_VALUE_SENTINEL


class TestBytesRedaction:
    def test_bytes_return_bytes_sentinel(self):
        assert sanitize_audit_value(b"secret bytes") == BYTES_SENTINEL

    def test_bytearray_return_bytes_sentinel(self):
        assert sanitize_audit_value(bytearray(b"x")) == BYTES_SENTINEL


class TestExceptionHandling:
    def test_exception_returns_safe_summary(self):
        result = sanitize_audit_value(ValueError("boom sk-secret"))
        assert isinstance(result, str)
        assert "ValueError" in result
        assert "sk-secret" not in result


class TestSecretValueRedaction:
    def test_bearer_token_redacted(self):
        assert redact_secret_like_string("Bearer abc.def.ghi") == REDACTED_SENTINEL

    def test_authorization_header_redacted(self):
        assert redact_secret_like_string("Authorization: Bearer xyz") == REDACTED_SENTINEL

    def test_sk_token_redacted(self):
        assert redact_secret_like_string("sk-abcd1234efgh5678ijkl") == REDACTED_SENTINEL

    def test_api_key_assignment_redacted(self):
        assert redact_secret_like_string("api_key=ABCDEF1234567890") == REDACTED_SENTINEL

    def test_pem_rsa_redacted(self):
        pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"
        assert redact_secret_like_string(pem) == REDACTED_SENTINEL

    def test_pem_ec_redacted(self):
        pem = "-----BEGIN EC PRIVATE KEY-----\nMHQ...\n-----END EC PRIVATE KEY-----"
        assert redact_secret_like_string(pem) == REDACTED_SENTINEL

    def test_pem_openssh_redacted(self):
        pem = "-----BEGIN OPENSSH PRIVATE KEY-----\nb3Bl...\n-----END OPENSSH PRIVATE KEY-----"
        assert redact_secret_like_string(pem) == REDACTED_SENTINEL

    def test_url_credentials_redacted(self):
        assert redact_secret_like_string("https://user:pass@example.com") == REDACTED_SENTINEL


class TestSecretFieldRedaction:
    def test_api_key_field_redacted(self):
        assert sanitize_audit_value("v", field_name="api_key") == REDACTED_SENTINEL

    def test_nested_secret_field_redacted(self):
        out = sanitize_audit_value({"config": {"clientSecret": "shh"}})
        assert out["config"]["clientSecret"] == REDACTED_SENTINEL

    def test_token_secret_field_redacted(self):
        assert sanitize_audit_value("x", field_name="tokenSecret") == REDACTED_SENTINEL

    def test_full_token_hash_field_redacted(self):
        assert sanitize_audit_value("h", field_name="fullTokenHash") == REDACTED_SENTINEL

    def test_raw_arguments_field_redacted(self):
        assert sanitize_audit_value("a", field_name="rawArguments") == REDACTED_SENTINEL

    def test_confirmation_token_id_allowed(self):
        # confirmationTokenId is a correlation id, not a secret — allowed.
        out = sanitize_audit_value("ctok_123", field_name="confirmationTokenId")
        assert out == "ctok_123"


class TestFullHashRedaction:
    def test_long_hex_redacted_as_token(self):
        full_hash = "a" * 64
        assert redact_token_like_string(full_hash) == REDACTED_SENTINEL

    def test_short_value_kept(self):
        assert redact_token_like_string("abc") == "abc"


class TestPathRedaction:
    def test_production_home_path_redacted(self):
        assert redact_path_like_string("/Users/huangruibang/.hermes/x") == REDACTED_SENTINEL

    def test_tilde_hermes_redacted(self):
        assert redact_path_like_string("~/.hermes/state.db") == REDACTED_SENTINEL

    def test_state_db_fragment_redacted(self):
        assert redact_path_like_string("/some/dir/state.db") == REDACTED_SENTINEL


class TestNestedContainers:
    def test_list_sanitized(self):
        out = sanitize_audit_value(["ok", b"bytes", lambda: 1, "sk-abcd1234efgh5678"])
        assert out[0] == "ok"
        assert out[1] == BYTES_SENTINEL
        assert out[2] == NON_JSON_VALUE_SENTINEL
        assert out[3] == REDACTED_SENTINEL

    def test_dict_sanitized(self):
        out = sanitize_audit_value({"a": 1, "b": {"c": "Bearer zzz"}})
        assert out["a"] == 1
        assert out["b"]["c"] == REDACTED_SENTINEL

    def test_depth_guard(self):
        nested = "x"
        for _ in range(20):
            nested = {"v": nested}
        out = sanitize_audit_value(nested)
        # Should not raise; deep values collapse to the truncation sentinel.
        assert isinstance(out, dict)


class TestLongStringTruncation:
    def test_long_string_truncated(self):
        # Use non-hex characters so the bare-hash redactor does not fire;
        # this isolates the truncation path.
        out = sanitize_audit_value("z" * 5000)
        assert out.endswith("…")
        assert len(out) <= 210


class TestMetadataSanitization:
    def test_metadata_returns_dict(self):
        out = sanitize_audit_metadata({"k": "v", "secret": "x"})
        assert isinstance(out, dict)
        assert out["secret"] == REDACTED_SENTINEL

    def test_none_metadata_returns_empty(self):
        assert sanitize_audit_metadata(None) == {}


class TestEventSanitization:
    def _good(self, **extra):
        ev = {
            "eventId": "e1", "sequence": 1,
            "createdAt": "2026-06-15T00:00:00+00:00",
            "eventType": "tool_dry_run", "auditKind": "dry_run",
            "schemaVersion": "audit_schema_v2",
        }
        ev.update(extra)
        return ev

    def test_event_secret_in_summary_redacted(self):
        ev = self._good(summary={"api_key": "sk-leak-1234567890abcdef"})
        out = sanitize_audit_event(ev)
        assert out["summary"]["api_key"] == REDACTED_SENTINEL

    def test_event_callable_in_metadata_collapsed(self):
        ev = self._good(safeMetadata={"cb": lambda: 1})
        out = sanitize_audit_event(ev)
        assert out["safeMetadata"]["cb"] == NON_JSON_VALUE_SENTINEL

    def test_event_falls_back_to_minimal_safe_on_garbage(self):
        out = sanitize_audit_event("not-a-dict")  # type: ignore[arg-type]
        assert out["schemaVersion"] == "audit_schema_v2"
        assert out["auditKind"] == "internal"

    def test_validate_sanitized_event_passes(self):
        ev = self._good()
        out = sanitize_audit_event(ev)
        ok, _ = validate_sanitized_event(out)
        assert ok

    def test_validate_sanitized_event_flags_forbidden(self):
        ok, reason = validate_sanitized_event(
            {"eventId": "e", "sequence": 1, "createdAt": "2026-06-15T00:00:00+00:00",
             "eventType": "t", "auditKind": "dry_run",
             "schemaVersion": "audit_schema_v2", "api_key": "not-redacted"}
        )
        assert not ok
        assert "forbidden" in reason


class TestCallableReprHelper:
    def test_redact_callable_repr(self):
        assert redact_callable_repr(object()) == NON_JSON_VALUE_SENTINEL


class TestJsonNativeGuarantee:
    def test_output_is_json_serializable(self):
        payload = {
            "a": [1, "x", b"bytes", {"k": lambda: 1}, "Bearer zzz"],
            "nested": {"api_key": "sk-abcd1234efgh5678", "ok": True},
        }
        out = sanitize_audit_value(payload)
        # Must serialize cleanly (no bytes / callable leak).
        round = json.dumps(out)
        assert "sk-abcd" not in round
        assert "Bearer" not in round
        assert "<lambda>" not in round
