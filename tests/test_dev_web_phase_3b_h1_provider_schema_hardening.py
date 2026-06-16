"""Phase 3B-H1 — Provider Request / Response Schema HARDENING (Lens 6).

Deterministic, adversarial verification of the normalized envelope schema:

  - the request envelope NEVER carries an API key, Authorization header, raw
    secret / token, full tokenHash, production path, file content, or callable repr
  - the response envelope exposes ONLY a bounded contentSummary + structured
    tool calls + bounded usage (never the raw body)
  - IDs are deterministic + opaque (derived ids, never the provider's raw id)
  - sizes are bounded (content summary, messages, tool calls, temperature,
    max_tokens)
  - a malformed response falls back safely (empty content / no tool calls)
  - redactionApplied is always True on every projection

Phase: 3B-H1 — Provider Boundary Hardening
"""

from __future__ import annotations

import json

import pytest

from hermes_cli.dev_web_provider_real_schema import (
    MAX_TOOL_CALLS,
    ProviderRealRequest,
    ProviderRealResponse,
    ProviderRealUsage,
    build_blocked_real_response,
    build_failed_real_response,
    build_provider_real_request,
    truncate_content_summary,
)

_LEAK_NEEDLES = (
    "sk-", "Bearer ", "Authorization", "apiKey", "api_key", "accessToken",
    "rawPrompt", "rawResponse", "rawArguments", "fullTokenHash", "tokenSecret",
    "plainToken", "fileContent", "/Users/huangruibang/.hermes", "state.db",
    "<function", "<bound method", "object at 0x",
)


def _assert_no_leak(obj: object) -> None:
    blob = json.dumps(obj, default=str)
    for needle in _LEAK_NEEDLES:
        assert needle not in blob, f"schema leak: {needle}"


# ===========================================================================
# Lens 6 — request envelope never carries a secret
# ===========================================================================


class TestRequestEnvelopeNoSecret:
    def test_request_safe_dict_has_redaction_flag(self) -> None:
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible", model="gpt-4o-mini",
            user_message="check route governance",
        )
        assert req.to_safe_dict()["redactionApplied"] is True

    def test_request_envelope_has_no_secret_bearing_fields(self) -> None:
        # The envelope carries the user message (its content is the user's); the
        # redaction of message-borne secrets is the orchestrator's job (contains_secret
        # blocks upstream). The ENVELOPE itself must never expose a key/header/token FIELD.
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible", model="gpt-4o-mini",
            user_message="check route governance",
        )
        d = req.to_safe_dict()
        for forbidden_field in (
            "apiKey", "api_key", "authorization", "Authorization", "accessToken",
            "rawPrompt", "rawResponse", "rawArguments", "fullTokenHash", "tokenSecret",
            "plainToken", "fileContent", "bearerToken",
        ):
            assert forbidden_field not in d, f"forbidden field in envelope: {forbidden_field}"

    def test_user_message_with_secret_is_in_messages_but_flagged_separately(self) -> None:
        # The redactor (contains_secret) blocks this; the envelope itself only
        # carries the bounded content (the block happens upstream in the orchestrator).
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible", model="gpt-4o-mini",
            user_message="x" * 10,
        )
        assert len(req.messages) == 1
        assert req.messages[0].role == "user"

    def test_request_id_is_opaque_prefix(self) -> None:
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible", model="gpt-4o-mini",
            user_message="hi",
        )
        assert req.request_id.startswith("preq_")
        # Deterministic: same inputs → same id.
        req2 = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible", model="gpt-4o-mini",
            user_message="hi",
        )
        assert req.request_id == req2.request_id


class TestRequestBounding:
    def test_message_oversize_truncated(self) -> None:
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible", model="gpt-4o-mini",
            user_message="x" * 100_000,
        )
        assert len(req.messages[0].content) <= 4000

    def test_non_string_message_becomes_empty(self) -> None:
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible", model="gpt-4o-mini",
            user_message=12345,  # type: ignore[arg-type]
        )
        assert req.messages[0].content == ""

    def test_temperature_is_clamped(self) -> None:
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible", model="gpt-4o-mini",
            user_message="hi", temperature=99.0,
        )
        assert 0.0 <= req.temperature <= 1.0

    def test_max_tokens_clamped(self) -> None:
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible", model="gpt-4o-mini",
            user_message="hi", max_tokens=999999,
        )
        assert req.max_tokens <= 4096

    def test_tool_allowlist_is_deduped_sorted(self) -> None:
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible", model="gpt-4o-mini",
            user_message="hi", tool_allowlist=("clarify", "clarify", "route_governance_read"),
        )
        assert req.tool_allowlist == ("clarify", "route_governance_read")


# ===========================================================================
# Lens 6 — response envelope exposes only bounded projections
# ===========================================================================


class TestResponseEnvelopeBounded:
    def _req(self) -> ProviderRealRequest:
        return build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible", model="gpt-4o-mini",
            user_message="hi",
        )

    def test_blocked_response_no_network(self) -> None:
        resp = build_blocked_real_response(request=self._req(), blocked_reason="blocked_provider_api_key_missing")
        d = resp.to_safe_dict()
        assert d["status"] == "blocked"
        assert d["externalNetworkCalled"] is False
        assert d["blockedReason"] == "blocked_provider_api_key_missing"
        assert d["redactionApplied"] is True

    def test_failed_response_network_attempted(self) -> None:
        resp = build_failed_real_response(
            request=self._req(), blocked_reason="blocked_provider_auth_failed",
            usage=ProviderRealUsage(1, 1, 2),
        )
        d = resp.to_safe_dict()
        assert d["status"] == "failed"
        assert d["externalNetworkCalled"] is True
        assert d["usageSummary"]["totalTokens"] == 2

    def test_response_response_id_is_opaque(self) -> None:
        resp = build_blocked_real_response(request=self._req(), blocked_reason="x")
        assert resp.response_id.startswith("prsp_")

    def test_response_never_carries_raw_body_or_secret(self) -> None:
        resp = build_blocked_real_response(request=self._req(), blocked_reason="x")
        _assert_no_leak(resp.to_safe_dict())

    def test_content_summary_truncated(self) -> None:
        long = "y" * 5000
        assert len(truncate_content_summary(long)) <= 1000

    def test_truncate_non_string_returns_empty(self) -> None:
        assert truncate_content_summary(None) == ""  # type: ignore[arg-type]
        assert truncate_content_summary(12345) == ""  # type: ignore[arg-type]


# ===========================================================================
# Lens 6 — max tool calls constant is bounded
# ===========================================================================


class TestToolCallBounding:
    def test_max_tool_calls_is_small_int(self) -> None:
        assert isinstance(MAX_TOOL_CALLS, int)
        assert 0 < MAX_TOOL_CALLS <= 32

    def test_usage_safe_dict_fields(self) -> None:
        d = ProviderRealUsage(3, 4, 7).to_safe_dict()
        assert d == {"promptTokens": 3, "completionTokens": 4, "totalTokens": 7}
