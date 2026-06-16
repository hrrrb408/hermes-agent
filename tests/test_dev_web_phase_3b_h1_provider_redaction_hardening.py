"""Phase 3B-H1 — Provider Secret / Authorization Redaction HARDENING.

Deterministic, adversarial verification of Lens 2 (Secret / Authorization
Redaction). The redactor must catch every secret carrier class, preserve token
COUNTS, collapse non-JSON values to a placeholder (never a repr / type name),
bound nesting depth, and drive blocking when a secret is detected.

  - sk-… / Bearer … / Authorization: … / every PEM variant are flagged
  - password / secret / token / credential / auth / apikey field-name string
    values are redacted (their INTEGER counts are preserved)
  - non-JSON-native values (callables, objects) collapse to <non_json_value>
    — NEVER the repr / type name / <function …> / object at 0x…
  - nesting depth is capped at 8 (deeper → dropped)
  - secret detection in request/response/arguments → blocked reason
  - the redacted output never carries a full tokenHash / raw token

Phase: 3B-H1 — Provider Boundary Hardening
Provider Secret Redaction ID: PROVIDER-SECRET-3B-H1-001
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_real_redaction import (
    BLOCKED_PROVIDER_SECRET_DETECTED,
    contains_secret,
    detect_secret_in_string,
    redact_real_payload,
)

_FORBIDDEN_LEAKS = (
    "<function", "<bound method", "<lambda", "object at 0x",
    "<class", "<module", "builtins.",
)


# ===========================================================================
# Lens 2 — secret value patterns (exhaustive)
# ===========================================================================


class TestSecretValuePatternsExhaustive:
    @pytest.mark.parametrize(
        "value",
        [
            "sk-abcdefghijklmnopqrstuvwxyz",
            "sk-proj-AbCdEf1234567890_-xyz",
            "Bearer abc.def.ghi.jkl",
            "bearer TOKENVALUE",
            "Authorization: Bearer sometoken",
            "authorization:Bearer xyz",
            "-----BEGIN RSA PRIVATE KEY-----",
            "-----BEGIN EC PRIVATE KEY-----",
            "-----BEGIN OPENSSH PRIVATE KEY-----",
            "-----BEGIN ENCRYPTED PRIVATE KEY-----",
            "-----BEGIN DSA PRIVATE KEY-----",
            "-----BEGIN PRIVATE KEY-----",
        ],
    )
    def test_detects_secret_in_string(self, value: str) -> None:
        assert detect_secret_in_string(value) is True

    @pytest.mark.parametrize(
        "value",
        [
            "hello world", "route_governance_read", "gpt-4o-mini", "12345", "",
            "api.openai.com", "openai_compatible", "completed", "blocked_provider_secret_detected",
            "redactionApplied", "env_present",
        ],
    )
    def test_safe_strings_not_flagged(self, value: str) -> None:
        assert detect_secret_in_string(value) is False

    def test_short_sk_not_flagged(self) -> None:
        # sk- with fewer than 8 trailing chars is NOT treated as a secret key
        # (avoids over-redacting the literal token stem).
        assert detect_secret_in_string("sk-abc") is False

    def test_blocked_reason_constant_is_frozen(self) -> None:
        assert BLOCKED_PROVIDER_SECRET_DETECTED == "blocked_provider_secret_detected"


# ===========================================================================
# Lens 2 — field-name redaction (string value → redacted; count → preserved)
# ===========================================================================


class TestFieldRedactionPrecision:
    @pytest.mark.parametrize("field", [
        "api_key", "apikey", "apiKey", "API_KEY", "api-key",
        "accessToken", "access_token", "ACCESS_TOKEN",
        "refresh_token", "refreshToken",
        "client_secret", "clientSecret",
        "password", "Password", "PASSWORD",
        "secret", "SECRET", "clientSecretValue",
        "credential", "credentials", "authToken", "privateKey",
    ])
    def test_secret_bearing_field_redacted(self, field: str) -> None:
        out = redact_real_payload({field: "any-nonempty-value"})
        assert out[field] == "[REDACTED]"

    @pytest.mark.parametrize("field", ["maxTokens", "promptTokens", "completionTokens", "totalTokens", "tokensToday"])
    def test_token_counts_preserved(self, field: str) -> None:
        out = redact_real_payload({field: 1024})
        assert out[field] == 1024

    def test_nested_token_counts_preserved(self) -> None:
        out = redact_real_payload({
            "usageSummary": {
                "promptTokens": 12, "completionTokens": 8, "totalTokens": 20,
            },
            "maxTokens": 1024,
        })
        assert out["usageSummary"]["totalTokens"] == 20
        assert out["maxTokens"] == 1024

    def test_empty_string_under_secret_field_is_safe(self) -> None:
        out = redact_real_payload({"api_key": ""})
        assert out["api_key"] == ""

    def test_bool_count_under_secret_field_preserved(self) -> None:
        out = redact_real_payload({"tokenValid": True})
        assert out["tokenValid"] is True


# ===========================================================================
# Lens 2 — non-JSON values collapse (NEVER a repr / type name)
# ===========================================================================


class TestNonJsonValueCollapse:
    def test_callable_collapsed_to_placeholder(self) -> None:
        def my_fn() -> None:  # pragma: no cover
            pass

        assert redact_real_payload({"handler": my_fn})["handler"] == "<non_json_value>"

    def test_object_collapsed_to_placeholder(self) -> None:
        class Secret:
            pass

        out = redact_real_payload({"obj": Secret()})
        assert out["obj"] == "<non_json_value>"

    def test_lambda_collapsed_to_placeholder(self) -> None:
        assert redact_real_payload({"fn": lambda: None})["fn"] == "<non_json_value>"

    def test_no_repr_or_type_name_leak_anywhere(self) -> None:
        class Secret:
            pass

        def my_fn() -> None:  # pragma: no cover
            pass

        blob = repr(redact_real_payload({
            "obj": Secret(), "fn": my_fn, "lambda": lambda: None,
            "nested": {"deep": {"callable": print}},
        }))
        for needle in _FORBIDDEN_LEAKS:
            assert needle not in blob, f"repr leak: {needle}"

    def test_set_collapsed_to_placeholder(self) -> None:
        # A set is not JSON-native; it must collapse, never iterate to repr.
        out = redact_real_payload({"ids": {1, 2, 3}})
        assert out["ids"] == "<non_json_value>"


# ===========================================================================
# Lens 2 — nesting depth bound at 8
# ===========================================================================


class TestDepthBound:
    def test_depth_eight_preserved(self) -> None:
        # Exactly depth 8 must survive; the leaf at depth 8 is kept.
        deep: dict = {}
        cur = deep
        for _ in range(7):
            cur["next"] = {}
            cur = cur["next"]
        cur["leaf"] = "safe-leaf-value"
        out = redact_real_payload(deep)
        assert "safe-leaf-value" in repr(out)

    def test_depth_over_eight_dropped(self) -> None:
        deep: dict = {}
        cur = deep
        for _ in range(15):
            cur["next"] = {}
            cur = cur["next"]
        cur["leaf"] = "deep-leak-value"
        blob = repr(redact_real_payload(deep))
        assert "deep-leak-value" not in blob


# ===========================================================================
# Lens 2 — secret detection drives blocking
# ===========================================================================


class TestSecretDetectionDrivesBlocking:
    def test_secret_in_message_content_blocks(self) -> None:
        payload = {"messages": [{"content": "my key is sk-leakedkey-1234567890"}]}
        assert contains_secret(payload) is True

    def test_secret_in_nested_arguments_blocks(self) -> None:
        payload = {"args": {"deep": {"header": "Authorization: Bearer abc.def.ghi"}}}
        assert contains_secret(payload) is True

    def test_safe_payload_not_blocked(self) -> None:
        payload = {
            "model": "gpt-4o-mini", "maxTokens": 1024,
            "usageSummary": {"totalTokens": 20},
            "messages": [{"content": "check route governance"}],
        }
        assert contains_secret(payload) is False

    @pytest.mark.parametrize("field", ["api_key", "accessToken", "client_secret", "password"])
    def test_secret_field_with_string_blocks(self, field: str) -> None:
        assert contains_secret({field: "anything"}) is True

    def test_secret_field_with_int_count_is_safe(self) -> None:
        assert contains_secret({"maxTokens": 1024}) is False
        assert contains_secret({"totalTokens": 999}) is False

    def test_secret_field_with_empty_string_is_safe(self) -> None:
        assert contains_secret({"api_key": ""}) is False

    def test_redacted_projection_has_no_raw_secret(self) -> None:
        payload = {
            "api_key": "sk-rawleakvalue-1234567890",
            "messages": [{"content": "Bearer abc.def.ghi"}],
        }
        out = redact_real_payload(payload)
        blob = repr(out)
        assert "sk-rawleakvalue" not in blob
        assert "abc.def.ghi" not in blob
        assert "[REDACTED]" in blob


# ===========================================================================
# Lens 2 — no full tokenHash / raw token leak
# ===========================================================================


class TestNoTokenHashLeak:
    def test_token_hash_field_string_redacted(self) -> None:
        out = redact_real_payload({"tokenHash": "deadbeefcafebabe1234567890abcdef"})
        assert out["tokenHash"] == "[REDACTED]"

    def test_plain_token_field_redacted(self) -> None:
        out = redact_real_payload({"plainToken": "abc123def456"})
        assert out["plainToken"] == "[REDACTED]"

    def test_redacted_output_is_json_serializable(self) -> None:
        import json

        def fn() -> None:  # pragma: no cover
            pass

        out = redact_real_payload({"handler": fn, "api_key": "sk-x", "maxTokens": 5})
        # Must round-trip through json without error.
        json.dumps(out)
