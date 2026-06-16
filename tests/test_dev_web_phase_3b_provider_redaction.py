"""Phase 3B — Real Provider Redaction / No-leak tests.

Verifies the redaction engine:
  - catches sk-… / Bearer … / Authorization: … / every PEM variant
  - redacts secret-bearing field-name string values
  - PRESERVES integer token counts (maxTokens, promptTokens, totalTokens …)
  - collapses non-JSON-native values (callables / objects) to <non_json_value>,
    never the repr / type name
  - bounds nesting depth to 8
  - secret detection drives blocking (blocked_provider_secret_detected)

Phase: 3B — Real Provider Read-only Controlled Integration
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_real_redaction import (
    BLOCKED_PROVIDER_SECRET_DETECTED,
    contains_secret,
    detect_secret_in_string,
    redact_real_payload,
)


class TestSecretValuePatterns:
    @pytest.mark.parametrize(
        "value",
        [
            "sk-abcdefghijklmnopqrstuvwxyz",
            "Bearer abc.def.ghi",
            "Authorization: Bearer sometoken",
            "-----BEGIN RSA PRIVATE KEY-----",
            "-----BEGIN EC PRIVATE KEY-----",
            "-----BEGIN OPENSSH PRIVATE KEY-----",
            "-----BEGIN ENCRYPTED PRIVATE KEY-----",
            "-----BEGIN PRIVATE KEY-----",
        ],
    )
    def test_detects_secret_in_string(self, value: str) -> None:
        assert detect_secret_in_string(value) is True

    @pytest.mark.parametrize(
        "value",
        ["hello world", "route_governance_read", "gpt-4o-mini", "12345", ""],
    )
    def test_safe_strings_not_flagged(self, value: str) -> None:
        assert detect_secret_in_string(value) is False

    def test_blocked_reason_constant(self) -> None:
        assert BLOCKED_PROVIDER_SECRET_DETECTED == "blocked_provider_secret_detected"


class TestFieldRedaction:
    def test_secret_field_string_value_redacted(self) -> None:
        out = redact_real_payload({"api_key": "sk-secretleak-1234567890"})
        assert out["api_key"] == "[REDACTED]"

    def test_access_token_redacted(self) -> None:
        out = redact_real_payload({"accessToken": "abc.def.ghi"})
        assert out["accessToken"] == "[REDACTED]"

    def test_client_secret_redacted(self) -> None:
        out = redact_real_payload({"client_secret": "hunter2"})
        assert out["client_secret"] == "[REDACTED]"

    def test_authorization_header_redacted(self) -> None:
        out = redact_real_payload({"authorization": "Bearer xyz"})
        assert out["authorization"] == "[REDACTED]"

    def test_token_counts_preserved(self) -> None:
        # The precision rule: token COUNTS under a secret-bearing name are ints
        # and must be preserved (not redacted).
        out = redact_real_payload({
            "maxTokens": 1024,
            "usageSummary": {
                "promptTokens": 12, "completionTokens": 8, "totalTokens": 20,
            },
            "tokensToday": 100,
        })
        assert out["maxTokens"] == 1024
        assert out["usageSummary"]["promptTokens"] == 12
        assert out["usageSummary"]["totalTokens"] == 20
        assert out["tokensToday"] == 100


class TestNonJsonValues:
    def test_callable_collapsed_to_placeholder(self) -> None:
        def my_fn() -> None:  # pragma: no cover
            pass

        out = redact_real_payload({"handler": my_fn})
        assert out["handler"] == "<non_json_value>"

    def test_never_renders_repr_or_type_name(self) -> None:
        class Secret:
            pass

        out = redact_real_payload({"obj": Secret(), "fn": lambda: None})
        blob = repr(out)
        assert "<function" not in blob
        assert "<bound method" not in blob
        assert "Secret" not in blob  # type name must not leak
        assert "lambda" not in blob


class TestDepthBound:
    def test_deeply_nested_value_dropped(self) -> None:
        deep: dict = {}
        cur = deep
        for _ in range(15):
            cur["next"] = {}
            cur = cur["next"]
        cur["leaf"] = "deep value"
        out = redact_real_payload(deep)
        blob = repr(out)
        # The depth cap drops the over-deep leaf (returns None along the path).
        assert "deep value" not in blob


class TestSecretDetection:
    def test_secret_in_request_payload_blocks(self) -> None:
        payload = {"messages": [{"content": "my key is sk-leakedkey-1234567890"}]}
        assert contains_secret(payload) is True

    def test_safe_payload_not_blocked(self) -> None:
        payload = {
            "model": "gpt-4o-mini", "maxTokens": 1024,
            "usageSummary": {"totalTokens": 20},
            "messages": [{"content": "check route governance"}],
        }
        assert contains_secret(payload) is False

    def test_forbidden_field_with_string_value_blocks(self) -> None:
        assert contains_secret({"api_key": "anything"}) is True
        assert contains_secret({"api_key": ""}) is False  # empty string is safe

    def test_forbidden_field_with_int_count_is_safe(self) -> None:
        assert contains_secret({"maxTokens": 1024}) is False
        assert contains_secret({"totalTokens": 999}) is False
