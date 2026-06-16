"""Phase 3B Real Provider Redaction + Secret Detection (Frozen).

Inherits the Phase 2B-H1 sanitizer SEMANTICS and extends them to the new
real-provider surfaces (request preview, response summary, cost badge,
blocked-reason panels). Nothing secret may ever reach an audit record, a log
line, a UI element, a doc, or a committed file.

If the sanitizer detects a secret in the request, response, or arguments, the
round-trip is **blocked** with ``blocked_provider_secret_detected`` — the
secret is never persisted, never returned, and never reaches the UI beyond the
redacted reason.

Important precision rule: a secret is a string-bearing value (an ``sk-…`` key,
a ``Bearer …`` token, an ``Authorization: …`` header, a PEM private key) OR a
string value under a secret-bearing field name (``api_key``, ``accessToken``,
``client_secret`` …). Integer token COUNTS (``maxTokens``, ``promptTokens``,
``totalTokens``, ``tokensToday``) are safe metadata and are preserved — they
are not secrets.

Phase: 3B — Real Provider Read-only Controlled Integration
Status: redaction implemented (Phase 2B-H1 semantics + token-count precision)
"""

from __future__ import annotations

import re
from typing import Any, Mapping

BLOCKED_PROVIDER_SECRET_DETECTED = "blocked_provider_secret_detected"

# Secret value patterns (frozen, widened in Phase 2B-H1 — the SAME patterns the
# Phase 2B sanitizer uses). These are the authoritative secret indicators.
_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    # Every PEM private-key variant (bare, RSA, EC, OPENSSH, DSA, ENCRYPTED...).
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
)

# Forbidden field-name stems whose STRING value is treated as a secret
# (defense-in-depth — mirrors Phase 2B-H1). An INTEGER value under such a name
# is a count (e.g. ``maxTokens``) and is preserved.
_FORBIDDEN_FIELD_STEMS: tuple[str, ...] = (
    "token", "secret", "password", "auth", "apikey", "privatekey", "credential",
)

_REDACTED_VALUE = "[REDACTED]"
_NON_JSON_PLACEHOLDER = "<non_json_value>"
_MAX_DEPTH = 8


def detect_secret_in_string(value: str) -> bool:
    """True if *value* matches a secret pattern (sk-…, Bearer …, Authorization, PEM)."""
    if not isinstance(value, str):
        return False
    return any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS)


def _is_secret_bearing_field(key: Any) -> bool:
    """True if the field NAME indicates a secret-bearing slot (substring stem)."""
    if not isinstance(key, str):
        return False
    normalized = key.strip().lower().replace("_", "").replace("-", "")
    return any(stem in normalized for stem in _FORBIDDEN_FIELD_STEMS)


def _is_count_value(value: Any) -> bool:
    """A safe count: int / float / bool / None under a secret-bearing field name."""
    return isinstance(value, (int, float, bool)) or value is None


def contains_secret(payload: Any, *, depth: int = 0) -> bool:
    """Recursively sweep a payload for secret values.

    A secret is:
      - a string matching a secret value pattern (sk-…, Bearer …, …), or
      - a STRING value under a secret-bearing field name (api_key, accessToken…).
    An integer token COUNT (maxTokens, promptTokens, totalTokens, tokensToday)
    under such a name is safe and does NOT trigger a block.

    Used to decide whether a request / response / arguments payload must be
    BLOCKED (``blocked_provider_secret_detected``) before any persistence.
    """
    if depth > _MAX_DEPTH:
        return False
    if isinstance(payload, str):
        return detect_secret_in_string(payload)
    if isinstance(payload, Mapping):
        for key, val in payload.items():
            if _is_secret_bearing_field(key):
                # A string value here is a secret; a count (int/bool/None) is safe.
                if isinstance(val, str):
                    if val:  # non-empty string under a secret-bearing field
                        return True
                elif isinstance(val, (dict, list, tuple)):
                    if contains_secret(val, depth=depth + 1):
                        return True
                # int/float/bool/None → a count, safe.
            else:
                if contains_secret(val, depth=depth + 1):
                    return True
        return False
    if isinstance(payload, (list, tuple)):
        return any(contains_secret(v, depth=depth + 1) for v in payload)
    # Non-JSON-native values (callables, objects) are not secrets per se, but
    # the redactor collapses them to a placeholder; they do not trigger a block.
    return False


def _redact(value: Any, *, depth: int = 0) -> Any:
    """Recursively redact secrets, preserve token counts, bound depth.

    Rules (mirror Phase 2B-H1, with the token-count precision rule):
      - a string matching a secret value pattern → ``[REDACTED]``;
      - a STRING value under a secret-bearing field name → ``[REDACTED]``;
      - an INTEGER / bool / None value under a secret-bearing field name →
        preserved (a token count);
      - nesting depth capped at 8 (deeper → None);
      - non-JSON-native values (callables, objects) → ``<non_json_value>``
        (never the repr / type name, which could leak a callable/function).
    """
    if depth > _MAX_DEPTH:
        return None
    if isinstance(value, str):
        if detect_secret_in_string(value):
            return _REDACTED_VALUE
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, val in value.items():
            if _is_secret_bearing_field(key) and isinstance(val, str) and val:
                out[str(key)] = _REDACTED_VALUE
                continue
            out[str(key)] = _redact(val, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [_redact(v, depth=depth + 1) for v in value]
    return _NON_JSON_PLACEHOLDER


def redact_real_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Run the Phase 3B redactor over a real-provider payload projection.

    Replaces secret-looking values + secret-field string values with
    ``[REDACTED]``, bounds nesting depth to 8, preserves token counts, and
    collapses non-JSON-native values to ``<non_json_value>``.
    """
    result = _redact(dict(payload) if payload else {}, depth=0)
    return result if isinstance(result, dict) else {}


def redact_real_request_for_audit(request_dict: Mapping[str, Any]) -> dict[str, Any]:
    """Redact a request envelope projection for audit / UI. Never a raw secret."""
    return redact_real_payload(request_dict)


def redact_real_response_for_audit(response_dict: Mapping[str, Any]) -> dict[str, Any]:
    """Redact a response envelope projection for audit / UI. Never a raw secret.

    The raw response body is never carried — only a bounded ``contentSummary``
    and structured tool calls. This function defensively re-redacts the whole
    projection before persistence or return.
    """
    return redact_real_payload(response_dict)


__all__ = [
    "BLOCKED_PROVIDER_SECRET_DETECTED",
    "detect_secret_in_string",
    "contains_secret",
    "redact_real_payload",
    "redact_real_request_for_audit",
    "redact_real_response_for_audit",
]
