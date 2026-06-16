"""Phase 3B OpenAI-compatible Provider Adapter (Gated Boundary).

The concrete adapter for the first real round-trip: a non-streaming OpenAI-
compatible ``POST /v1/chat/completions``. It is exercised ONLY through the gated
real round-trip orchestrator and ONLY with an **injected** HTTP client. Tests
inject a ``MockHttpClient``; there is **no default real-network client wired
into the live request path**, so no real provider call ever happens in tests,
smoke, or default operation.

Design constraints (frozen):
  - The HTTP client is a Protocol injected by the caller (mock in tests).
  - Connect / read / total timeouts are bounded; max-response-size is bounded.
  - Retries are capped and run ONLY on safe-transient errors (bounded backoff).
  - No retry on auth failure, policy-block, budget, secret-detected, or oversize.
  - The API key is read once from the env into a local variable, attached to a
    single outbound header, and dropped after the call. It is NEVER captured
    into any application data structure, NEVER returned, NEVER audited.
  - Every response is normalized to a bounded summary + structured tool calls;
    the raw body is never returned.
  - Malformed JSON / schema mismatch / unknown tool / oversize → blocked (never
    repaired via eval/exec).

Phase: 3B — Real Provider Read-only Controlled Integration
Status: OpenAI-compatible adapter implemented (gated; mock-only in tests)
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from hermes_cli.dev_web_provider_openai_compatible_schema import (
    OpenAIChatRequest,
    OpenAIChatResponse,
    parse_openai_chat_response,
)
from hermes_cli.dev_web_provider_real_policy import (
    BLOCKED_PROVIDER_AUTH_FAILED,
    BLOCKED_PROVIDER_MALFORMED_RESPONSE,
    BLOCKED_PROVIDER_NETWORK_UNAVAILABLE,
    BLOCKED_PROVIDER_RESPONSE_TOO_LARGE,
    BLOCKED_PROVIDER_RETRY_EXHAUSTED,
    BLOCKED_PROVIDER_SCHEMA_MISMATCH,
    BLOCKED_PROVIDER_TIMEOUT_INVALID,
    classify_http_failure,
    is_auth_failure,
    is_safe_transient_failure,
)

_MAX_RESPONSE_BYTES = 64 * 1024  # 64 KiB hard ceiling on a response body.
_BACKOFF_BASE_SECONDS = 0.2  # bounded exponential backoff base (no unbounded growth)
_BACKOFF_CAP_SECONDS = 2.0


# ---------------------------------------------------------------------------
# 1. Injectable HTTP client Protocol + raw response
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RawHttpResponse:
    """The raw wire response an injected client returns.

    ``body`` is the raw bytes (or None on a transport failure). The adapter
    enforces the size limit and never returns the raw body to the caller.
    """

    status: int | None  # None => transport-level failure (no HTTP status)
    body: bytes | None
    error: str | None  # a transport error label, value-free (no secret)


class ProviderHttpClient(Protocol):
    """The injectable HTTP client contract.

    A concrete production client (stdlib ``urllib``) exists but is NEVER wired
    into the live request path by default; tests inject ``MockHttpClient``.
    """

    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
        *,
        timeout_seconds: int,
        max_response_bytes: int,
    ) -> RawHttpResponse:
        """Perform a single bounded HTTPS POST. Never raises to the adapter."""
        ...


class MockHttpClient:
    """A deterministic, offline mock HTTP client for tests.

    Returns a canned response and records each call (url / header KEYS / body)
    so tests can assert the request shape and the no-leak invariant. It NEVER
    performs a real network call and NEVER retains an API-key value beyond the
    single recorded ``header_keys`` set (keys only, never values).
    """

    def __init__(
        self,
        *,
        response_body: bytes | None = None,
        response_status: int = 200,
        error: str | None = None,
        responses: tuple[RawHttpResponse, ...] | None = None,
    ) -> None:
        self._single = RawHttpResponse(
            status=response_status, body=response_body, error=error,
        )
        self._responses = responses
        self._index = 0
        self.calls: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
        *,
        timeout_seconds: int,
        max_response_bytes: int,
    ) -> RawHttpResponse:
        # Record KEYS only (never the Authorization / API-key value).
        self.calls.append(
            {
                "url": url,
                "headerKeys": tuple(sorted(headers.keys())),
                "bodyBytes": len(body) if isinstance(body, (bytes, bytearray)) else 0,
                "timeoutSeconds": timeout_seconds,
                "maxResponseBytes": max_response_bytes,
            }
        )
        if self._responses is not None:
            if self._index < len(self._responses):
                resp = self._responses[self._index]
                self._index += 1
                return resp
            return RawHttpResponse(status=None, body=None, error="mock_exhausted")
        return self._single


# ---------------------------------------------------------------------------
# 2. Adapter round-trip result (normalized, never raw)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AdapterRoundTripResult:
    """The adapter's normalized result for the orchestrator to redact + audit.

    ``raw_tool_calls`` are provider-shaped tool calls (id / function name /
    arguments) NOT yet validated against the allowlist — the orchestrator does
    that. No raw response body, header, or secret is ever carried here.
    """

    ok: bool
    content: str
    raw_tool_calls: tuple[Mapping[str, Any], ...]
    usage: Mapping[str, Any]
    finish_reason: str
    blocked_reason: str | None
    http_status: int | None
    attempts: int
    external_network_called: bool


# ---------------------------------------------------------------------------
# 3. The adapter
# ---------------------------------------------------------------------------


def _read_api_key_once() -> str | None:
    """Read the API key from the env ONCE into a local; return it or None.

    The returned value lives only in the caller's local scope for the duration
    of the HTTP call and is then dropped. It is never logged, audited, or
    captured into a data structure. (Placeholder keys are accepted; the live
    path is gated so this is only reached under explicit enablement.)
    """
    for env_name in (
        "HERMES_PROVIDER_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "XAI_API_KEY",
        "ZAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        value = os.environ.get(env_name, "")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _backoff_seconds(attempt: int) -> float:
    """Bounded exponential backoff (base * 2^attempt), capped — no growth storm."""
    return min(_BACKOFF_CAP_SECONDS, _BACKOFF_BASE_SECONDS * (2 ** attempt))


class OpenAICompatibleAdapter:
    """OpenAI-compatible non-streaming chat-completions adapter.

    Constructed with an injected ``http_client`` and the bounded config. The
    ``round_trip`` method builds the request, performs the bounded call with
    retry, and normalizes the response. No raw body / header / secret is ever
    returned.
    """

    def __init__(self, http_client: ProviderHttpClient, *, base_url: str, model: str) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")
        self._model = model

    def round_trip(
        self,
        request,
        *,
        timeout_seconds: int,
        max_retries: int,
    ) -> AdapterRoundTripResult:
        """Perform one bounded, retry-capped real round-trip.

        ``request`` is a ``ProviderRealRequest``. Returns an
        ``AdapterRoundTripResult`` for the orchestrator.
        """
        if timeout_seconds < 1:
            return AdapterRoundTripResult(
                ok=False, content="", raw_tool_calls=(), usage={},
                finish_reason="blocked",
                blocked_reason=BLOCKED_PROVIDER_TIMEOUT_INVALID,
                http_status=None, attempts=0, external_network_called=False,
            )

        api_key = _read_api_key_once()
        # The Authorization header is built and immediately passed to the client.
        # It is never stored on ``self`` or in any returned structure.
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        else:
            # Gating should have blocked this already; defense-in-depth.
            headers["Authorization"] = "Bearer <none>"

        chat_request = OpenAIChatRequest.from_real_request(request, model=self._model)
        body = json.dumps(chat_request.to_payload()).encode("utf-8")
        url = f"{self._base_url}/v1/chat/completions"

        attempts = 0
        last_status: int | None = None
        last_reason: str | None = None
        for attempt in range(max_retries + 1):
            attempts = attempt + 1
            raw = self._client.post(
                url, headers, body,
                timeout_seconds=timeout_seconds,
                max_response_bytes=_MAX_RESPONSE_BYTES,
            )
            last_status = raw.status

            # Transport-level failure (no HTTP status).
            if raw.status is None:
                last_reason = BLOCKED_PROVIDER_NETWORK_UNAVAILABLE
                if attempt < max_retries and is_safe_transient_failure(
                    http_status=None, blocked_reason=BLOCKED_PROVIDER_NETWORK_UNAVAILABLE,
                ):
                    time.sleep(_backoff_seconds(attempt))
                    continue
                return self._fail(last_reason, attempts)

            # Response-size guard (non-retryable).
            if isinstance(raw.body, (bytes, bytearray)) and len(raw.body) > _MAX_RESPONSE_BYTES:
                return self._fail(BLOCKED_PROVIDER_RESPONSE_TOO_LARGE, attempts)

            # Auth failure (non-retryable).
            if is_auth_failure(raw.status):
                return self._fail(BLOCKED_PROVIDER_AUTH_FAILED, attempts)

            # Success or a client/server error we must classify.
            if 200 <= raw.status < 300:
                return self._normalize(raw, attempts)

            classified = classify_http_failure(raw.status)
            last_reason = classified
            if attempt < max_retries and is_safe_transient_failure(
                http_status=raw.status, blocked_reason=None,
            ):
                time.sleep(_backoff_seconds(attempt))
                continue
            return self._fail(classified, attempts)

        # Retry cap exhausted (safe-transient storm).
        reason = last_reason or BLOCKED_PROVIDER_RETRY_EXHAUSTED
        return AdapterRoundTripResult(
            ok=False, content="", raw_tool_calls=(), usage={},
            finish_reason="failed", blocked_reason=BLOCKED_PROVIDER_RETRY_EXHAUSTED,
            http_status=last_status, attempts=attempts, external_network_called=True,
        )

    @staticmethod
    def _fail(reason: str, attempts: int) -> AdapterRoundTripResult:
        return AdapterRoundTripResult(
            ok=False, content="", raw_tool_calls=(), usage={},
            finish_reason="failed", blocked_reason=reason,
            http_status=None, attempts=attempts, external_network_called=True,
        )

    def _normalize(self, raw: RawHttpResponse, attempts: int) -> AdapterRoundTripResult:
        body = raw.body or b""
        try:
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return self._fail(BLOCKED_PROVIDER_MALFORMED_RESPONSE, attempts)
        if not isinstance(payload, dict):
            return self._fail(BLOCKED_PROVIDER_SCHEMA_MISMATCH, attempts)

        try:
            parsed: OpenAIChatResponse = parse_openai_chat_response(payload)
        except ValueError:
            return self._fail(BLOCKED_PROVIDER_SCHEMA_MISMATCH, attempts)

        return AdapterRoundTripResult(
            ok=True,
            content=parsed.content,
            raw_tool_calls=tuple(parsed.tool_calls),
            usage=dict(parsed.usage),
            finish_reason=parsed.finish_reason,
            blocked_reason=None,
            http_status=raw.status,
            attempts=attempts,
            external_network_called=True,
        )


__all__ = [
    "ProviderHttpClient",
    "RawHttpResponse",
    "MockHttpClient",
    "AdapterRoundTripResult",
    "OpenAICompatibleAdapter",
    "MAX_RESPONSE_BYTES",
]


# Re-exported size constant for tests.
MAX_RESPONSE_BYTES = _MAX_RESPONSE_BYTES
