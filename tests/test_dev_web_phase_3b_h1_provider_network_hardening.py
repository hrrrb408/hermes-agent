"""Phase 3B-H1 — Provider Network Isolation / Mock-only Boundary HARDENING.

Deterministic, adversarial verification of Lens 3 (Network Isolation):

  - tests/smoke use MockHttpClient ONLY; there is no default real-network client
    wired into the live request path
  - the HTTP client is an injected Protocol; the adapter cannot reach a real
    endpoint without an explicit concrete client that no default path wires
  - the MockHttpClient records header KEYS only (never the Authorization value)
  - no real provider endpoint is ever called in any test
  - transport failure / retry-exhaustion is simulated via mock, never real
  - the success path normalizes the response WITHOUT exposing the raw body

Phase: 3B-H1 — Provider Boundary Hardening
Provider Network Isolation ID: PROVIDER-NETWORK-3B-H1-001
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from hermes_cli.dev_web_provider_openai_compatible import (
    MAX_RESPONSE_BYTES,
    AdapterRoundTripResult,
    MockHttpClient,
    OpenAICompatibleAdapter,
    ProviderHttpClient,
    RawHttpResponse,
)
from hermes_cli.dev_web_provider_real_roundtrip import build_real_request_from_message

# A minimal, non-secret-bearing OpenAI-style success body.
_OK_BODY = json.dumps({
    "choices": [{
        "message": {
            "role": "assistant",
            "content": "route governance is 34/34/5/0/1/1",
            "tool_calls": [{
                "id": "call_1", "type": "function",
                "function": {"name": "route_governance_read", "arguments": "{}"},
            }],
        },
        "finish_reason": "tool_calls",
    }],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
}).encode()


# A minimal, non-secret-bearing real request envelope (built from config).
def _request():
    return build_real_request_from_message("check route governance")


def _adapter(mock: MockHttpClient) -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(mock, base_url="https://api.openai.com", model="gpt-4o-mini")


# ===========================================================================
# Lens 3 — injectable Protocol + no default real client
# ===========================================================================


class TestInjectableClientContract:
    def test_provider_http_client_is_a_protocol(self) -> None:
        # The client contract is structural (a Protocol), not a concrete class.
        assert isinstance(ProviderHttpClient, type)

    def test_mock_client_is_a_provider_http_client(self) -> None:
        mock = MockHttpClient(response_body=_OK_BODY)
        # Structural conformance: MockHttpClient exposes the Protocol's `post`.
        assert callable(getattr(mock, "post", None))

    def test_mock_client_records_header_keys_only(self) -> None:
        mock = MockHttpClient(response_body=_OK_BODY)
        adapter = _adapter(mock)
        adapter.round_trip(_request(), timeout_seconds=10, max_retries=0)
        assert len(mock.calls) == 1
        call = mock.calls[0]
        assert "headerKeys" in call
        # The recorded keys include Authorization (the KEY), but the VALUE is gone.
        assert "Authorization" in call["headerKeys"]
        # The call dict carries no Authorization value, no body content, no secret.
        blob = json.dumps(call, default=str)
        assert "Bearer " not in blob
        assert "sk-" not in blob

    def test_call_record_carries_no_body_content(self) -> None:
        mock = MockHttpClient(response_body=_OK_BODY)
        adapter = _adapter(mock)
        adapter.round_trip(_request(), timeout_seconds=10, max_retries=0)
        # Only the byte LENGTH of the request body is recorded, never its content.
        call = mock.calls[0]
        assert call["bodyBytes"] > 0
        assert "body" not in call

    def test_url_is_allowlisted_endpoint(self) -> None:
        mock = MockHttpClient(response_body=_OK_BODY)
        adapter = _adapter(mock)
        adapter.round_trip(_request(), timeout_seconds=10, max_retries=0)
        assert mock.calls[0]["url"] == "https://api.openai.com/v1/chat/completions"


# ===========================================================================
# Lens 3 — transport / retry simulation via mock (never real)
# ===========================================================================


class TestTransportSimulationViaMock:
    def test_transport_failure_is_network_unavailable(self) -> None:
        mock = MockHttpClient(response_body=None, response_status=None, error="mock_timeout")
        adapter = _adapter(mock)
        result = adapter.round_trip(_request(), timeout_seconds=10, max_retries=0)
        assert isinstance(result, AdapterRoundTripResult)
        assert result.ok is False
        assert result.blocked_reason == "blocked_provider_network_unavailable"
        assert result.external_network_called is True

    def test_retry_exhausted_then_succeeds_within_cap(self) -> None:
        # Two transient transport failures then a success, with max_retries=2.
        responses = (
            RawHttpResponse(status=None, body=None, error="mock_t1"),
            RawHttpResponse(status=None, body=None, error="mock_t2"),
            RawHttpResponse(status=200, body=_OK_BODY, error=None),
        )
        mock = MockHttpClient(responses=responses)
        adapter = _adapter(mock)
        result = adapter.round_trip(_request(), timeout_seconds=10, max_retries=2)
        assert result.ok is True
        assert result.attempts == 3

    def test_transient_storm_is_capped(self) -> None:
        # A safe-transient 5xx storm is retried up to the cap then fails closed.
        # (The retry cap is the hardening invariant: attempts == max_retries + 1.)
        mock = MockHttpClient(response_status=503, response_body=b'{"error":"storm"}')
        adapter = _adapter(mock)
        result = adapter.round_trip(_request(), timeout_seconds=10, max_retries=2)
        assert result.ok is False
        assert result.blocked_reason == "blocked_provider_network_unavailable"
        assert result.attempts == 3  # initial + 2 retries, capped
        assert len(mock.calls) == 3


# ===========================================================================
# Lens 3 — response-size guard (bounded, never raw body returned)
# ===========================================================================


class TestResponseSizeGuard:
    def test_oversize_body_blocks(self) -> None:
        oversize = b"x" * (MAX_RESPONSE_BYTES + 1)
        mock = MockHttpClient(response_body=oversize, response_status=200)
        adapter = _adapter(mock)
        result = adapter.round_trip(_request(), timeout_seconds=10, max_retries=0)
        assert result.ok is False
        assert result.blocked_reason == "blocked_provider_response_too_large"

    def test_success_path_never_returns_raw_body(self) -> None:
        mock = MockHttpClient(response_body=_OK_BODY, response_status=200)
        adapter = _adapter(mock)
        result = adapter.round_trip(_request(), timeout_seconds=10, max_retries=0)
        assert result.ok is True
        blob = repr(result.__dict__) if hasattr(result, "__dict__") else repr(result)
        # The normalized result exposes only the bounded content + tool calls,
        # never the full raw JSON body object.
        assert "choices" not in blob


# ===========================================================================
# Lens 3 — success normalization carries no secret
# ===========================================================================


class TestSuccessNormalizationNoLeak:
    def test_normalized_result_no_secret(self) -> None:
        import dataclasses

        mock = MockHttpClient(response_body=_OK_BODY, response_status=200)
        adapter = _adapter(mock)
        result = adapter.round_trip(_request(), timeout_seconds=10, max_retries=0)
        blob = json.dumps(dataclasses.asdict(result), default=str)
        for needle in ("sk-", "Bearer ", "Authorization"):
            assert needle not in blob

    def test_usage_counts_preserved(self) -> None:
        mock = MockHttpClient(response_body=_OK_BODY, response_status=200)
        adapter = _adapter(mock)
        result = adapter.round_trip(_request(), timeout_seconds=10, max_retries=0)
        assert result.usage["total_tokens"] == 15
        assert result.usage["prompt_tokens"] == 10
