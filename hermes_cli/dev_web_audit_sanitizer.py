"""Unified Audit Sanitizer for the Hermes Dev WebUI (Phase 2D).

This is the **single** redaction surface for every audit event that enters the
durable audit store. It replaces the per-writer defensive sanitizers (the
dry-run / pre-execution / post-execution / provider / write / rollback /
confirmation writers each had their own copy) and closes the Phase 2A
defense-in-depth gap where the dry-run sanitizer fell back to ``str(value)``
for unknown types — which can leak callable / function / object reprs.

Hard guarantees:
  - Non-JSON-native values NEVER use ``str(value)``. Callables, functions,
    arbitrary objects, and ``object at 0x...`` reprs collapse to the literal
    sentinel ``"<non_json_value>"``.
  - ``bytes`` collapse to ``"<bytes_redacted>"``.
  - ``Exception`` objects collapse to a safe summary (class name only).
  - Secret-like keys are redacted regardless of value.
  - Secret-like values (PEM blocks, ``sk-...``, ``Bearer ...``, ``Authorization:``,
    ``api_key=...``) are redacted.
  - Full token hashes and raw arguments are redacted.
  - Paths that reference the production home or ``~/.hermes`` are redacted.
  - Long strings are truncated to a bounded length.

Phase: 2D — Durable Dev Audit Store MVP
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from hermes_cli.dev_web_audit_schema import (
    AUDIT_SCHEMA_VERSION,
    validate_canonical_event,
)

# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

#: Sentinel returned for any non-JSON-native value (callable, object, etc.).
#: This is the explicit replacement for the old ``str(value)`` fallback.
NON_JSON_VALUE_SENTINEL = "<non_json_value>"
BYTES_SENTINEL = "<bytes_redacted>"
REDACTED_SENTINEL = "[REDACTED]"

#: Default truncation length for sanitized string scalars.
MAX_STRING_LENGTH = 200

#: Maximum nesting depth before a value is collapsed (cycle / runaway guard).
_MAX_DEPTH = 8

#: Production home — never echoed, even in path form.
_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"

# ---------------------------------------------------------------------------
# 2. Secret value patterns
# ---------------------------------------------------------------------------

# These match VALUES (not keys). A value that matches any of these is replaced
# with the redaction sentinel wholesale.
_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Anthropic / OpenAI style ``sk-...`` tokens (>= 16 payload chars)
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    # Bearer / Authorization headers
    re.compile(r"(?i)bearer\s+\S+"),
    re.compile(r"(?i)authorization\s*:\s*\S+"),
    re.compile(r"(?i)api[_\-]?key\s*[:=]\s*\S+"),
    # PEM private key blocks (any algorithm variant)
    re.compile(r"-----BEGIN\s+(?:RSA\s+|EC\s+|OPENSSH\s+|PGP\s+|ENCRYPTED\s+|PRIVATE\s+)?PRIVATE\s+KEY-----"),
    # Git-style credentials embedded in URLs: https://user:pass@host
    re.compile(r"(?i)https?://[^\s/@:]+:[^\s/@]+@"),
)

# Callable / function / object repr fingerprints. These are caught by the
# non-JSON-native branch first, but we also scrub them out of any string that
# happens to contain them (defense-in-depth for serialized error messages).
_CALLABLE_REPR_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"<function\s[^>]*>"),
    re.compile(r"<bound\s+method\s[^>]*>"),
    re.compile(r"<[A-Za-z_][A-Za-z0-9_.]*\s+object\s+at\s+0x[0-9a-fA-F]+>"),
    re.compile(r"<built-in\s+function\s[^>]*>"),
    re.compile(r"<class\s+[^>]*>"),
)

# Forbidden field-name stems. A key whose normalized form matches one of these
# is redacted regardless of its value. Covers the full Phase 2D surface.
_FORBIDDEN_FIELD_STEMS: frozenset[str] = frozenset(
    n.replace("_", "").replace("-", "").lower()
    for n in (
        "api_key", "apikey", "authorization", "auth_header", "auth", "bearer",
        "token", "tokens", "secret", "secrets", "password", "passwd",
        "credential", "credentials", "cookie", "cookies", "session",
        "private_key", "client_secret", "access_token", "refresh_token",
        "access_key", "id_token", "jwt", "signature",
        # audit-specific raw fields — never persisted verbatim
        "rawarguments", "arguments", "argumentspreview",
        "rawargumentspreview", "rawargs", "args",
        "tokenhash", "fulltokenhash", "rawtoken", "plaintoken",
        "confirmationtoken", "confirmationtokensecret",
        "tokensecret", "filecontent", "rawfilecontent",
        "providerpayload", "providerrequestpayload", "providerresponsepayload",
    )
)

# Field stems that are explicitly ALLOWED as correlation IDs (despite
# containing "token" / "id"). These are opaque ids, not secrets.
_ALLOWED_ID_STEMS: frozenset[str] = frozenset(
    n.replace("_", "").replace("-", "").lower()
    for n in (
        "confirmationTokenId",
        "tokenId",  # an id referring to a token, not the token itself
    )
)

# Production path fragments that must never appear in a sanitized value.
_FORBIDDEN_PATH_FRAGMENTS: tuple[str, ...] = (
    "/Users/huangruibang/.hermes",
    "~/.hermes",
    "state.db",
)


# ---------------------------------------------------------------------------
# 3. Low-level redaction helpers
# ---------------------------------------------------------------------------


def _normalize_field_name(name: Any) -> str:
    """Normalize a field name for stem comparison."""
    if not isinstance(name, str):
        return ""
    return name.replace("_", "").replace("-", "").lower()


def redact_secret_like_string(value: str) -> str:
    """Redact secret-like patterns inside a string value.

    Returns the (possibly partially redacted) string. Whole-string secrets are
    collapsed to ``REDACTED_SENTINEL``; embedded callable reprs are scrubbed.
    """
    if not isinstance(value, str):
        return value  # type: ignore[return-value]
    # If the entire value is a single secret token, redact wholesale.
    for pattern in _SECRET_VALUE_PATTERNS:
        if pattern.fullmatch(value.strip()):
            return REDACTED_SENTINEL
    # Otherwise scrub embedded callable / object reprs and production paths.
    out = value
    for pattern in _CALLABLE_REPR_PATTERNS:
        out = pattern.sub(NON_JSON_VALUE_SENTINEL, out)
    # Catch-all: any residual Python repr fingerprint (nested-class reprs like
    # ``<...<locals>.Foo object at 0x...>`` defeat the structured patterns) →
    # redact the whole string rather than risk a leak.
    for fingerprint in (" object at 0x", "<function", "<bound method",
                        "<built-in function", "<class ", "<module "):
        if fingerprint in out:
            out = REDACTED_SENTINEL
            break
    for frag in _FORBIDDEN_PATH_FRAGMENTS:
        if frag in out:
            out = REDACTED_SENTINEL
            break
    # Scrub embedded secret tokens that appear inside a larger string.
    for pattern in _SECRET_VALUE_PATTERNS:
        if pattern.search(out):
            out = REDACTED_SENTINEL
            break
    return out


def redact_path_like_string(value: str) -> str:
    """Redact path-like strings that reference production locations."""
    if not isinstance(value, str):
        return value  # type: ignore[return-value]
    for frag in _FORBIDDEN_PATH_FRAGMENTS:
        if frag in value:
            return REDACTED_SENTINEL
    return value


def redact_token_like_string(value: str) -> str:
    """Redact token-like strings (opaque secrets, full hashes)."""
    if not isinstance(value, str):
        return value  # type: ignore[return-value]
    # A bare HEX digest >= 32 chars (no dashes/underscores) is treated as a
    # full hash/secret. UUIDs (which contain dashes) and short correlation
    # ids are preserved.
    if len(value) >= 32 and re.fullmatch(r"[0-9a-fA-F]+", value):
        return REDACTED_SENTINEL
    return redact_secret_like_string(value)


def redact_callable_repr(value: Any) -> str:
    """Return the safe sentinel for any callable / non-JSON-native value.

    This is the explicit replacement for the old ``str(value)`` fallback.
    """
    return NON_JSON_VALUE_SENTINEL


def _is_forbidden_field(key: Any) -> bool:
    """Return ``True`` if *key* is a secret-like field name."""
    norm = _normalize_field_name(key)
    if not norm:
        return False
    if norm in _ALLOWED_ID_STEMS:
        return False
    # Substring match against forbidden stems (catches ``confirmationToken``,
    # ``api_key_v2`` etc. without enumerating every variant).
    return any(norm == stem or stem in norm for stem in _FORBIDDEN_FIELD_STEMS)


# ---------------------------------------------------------------------------
# 4. Recursive value sanitizer
# ---------------------------------------------------------------------------


def sanitize_audit_value(
    value: Any,
    *,
    field_name: str | None = None,
    depth: int = 0,
) -> Any:
    """Recursively sanitize a single value for audit storage / output.

    This is the core routine. It guarantees the result is JSON-native
    (``None`` / ``bool`` / ``int`` / ``float`` / ``str`` / sanitized ``dict``
    / sanitized ``list``) and contains no secrets, callable reprs, bytes, or
    production paths.
    """
    if depth > _MAX_DEPTH:
        return "[truncated: depth exceeded]"

    # Redact forbidden fields first — value never reaches the type branches.
    if field_name is not None and _is_forbidden_field(field_name):
        return REDACTED_SENTINEL

    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value

    if isinstance(value, str):
        # Apply secret-pattern + bare-hash (full tokenHash) redaction.
        redacted = redact_token_like_string(value)
        if len(redacted) > MAX_STRING_LENGTH:
            return redacted[:MAX_STRING_LENGTH] + "…"
        return redacted

    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for k, v in value.items():
            # Sanitize the key itself (keys can carry secret names too).
            if not isinstance(k, str):
                k = NON_JSON_VALUE_SENTINEL
            else:
                k = redact_secret_like_string(k)
            out[k] = sanitize_audit_value(v, field_name=k, depth=depth + 1)
        return out

    if isinstance(value, (list, tuple, set, frozenset)):
        return [
            sanitize_audit_value(item, field_name=field_name, depth=depth + 1)
            for item in value
        ]

    # ---- Non-JSON-native values: NEVER use str(value) ----
    if isinstance(value, (bytes, bytearray)):
        return BYTES_SENTINEL
    if isinstance(value, BaseException):
        # Safe summary: class name only, never the message (may leak secrets).
        return f"<exception:{type(value).__name__}>"

    # Callables, functions, arbitrary objects, classes, modules, etc.
    return NON_JSON_VALUE_SENTINEL


def sanitize_audit_metadata(metadata: Any) -> dict[str, Any]:
    """Sanitize a free-form metadata mapping into a safe JSON dict.

    Always returns a dict (possibly empty). Never raises.
    """
    if metadata is None:
        return {}
    sanitized = sanitize_audit_value(metadata, field_name="safeMetadata")
    if isinstance(sanitized, dict):
        return sanitized
    return {}


def strip_forbidden_keys(value: Any) -> Any:
    """Recursively DROP forbidden field keys entirely (not just redact values).

    Used for OUTPUT sanitization where even a redacted forbidden key name
    (``rawArguments``, ``tokenHash``, ``api_key`` …) must not be surfaced.
    Values that are not dicts/lists pass through unchanged.
    """
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if isinstance(k, str) and _is_forbidden_field(k):
                continue
            out[k] = strip_forbidden_keys(v)
        return out
    if isinstance(value, list):
        return [strip_forbidden_keys(v) for v in value]
    return value


# ---------------------------------------------------------------------------
# 5. Full event sanitizer
# ---------------------------------------------------------------------------


def sanitize_audit_event(event: Any) -> dict[str, Any]:
    """Sanitize a complete canonical audit event dict.

    - Validates the canonical shape; on failure returns a minimal safe event.
    - Applies recursive value sanitization to ``summary`` and ``safeMetadata``.
    - Re-validates after sanitization; on any anomaly returns the minimal
      safe event so the store writer never persists a leaky record.
    """
    if not isinstance(event, dict):
        return _minimal_safe_event()

    # Copy canonical scalar/flag fields through, then sanitize containers.
    out: dict[str, Any] = {}
    for key, value in event.items():
        if not isinstance(key, str):
            continue
        # Containers are sanitized recursively; scalars are passed through the
        # scalar sanitizer (which redacts secrets / callable reprs).
        if key in ("summary", "safeMetadata"):
            out[key] = sanitize_audit_metadata(value)
        else:
            out[key] = sanitize_audit_value(value, field_name=key)

    # Enforce schema version.
    out["schemaVersion"] = AUDIT_SCHEMA_VERSION

    ok, _reason = validate_canonical_event(out)
    if not ok:
        return _minimal_safe_event(event_type=out.get("eventType"))
    return out


def validate_sanitized_event(event: Any) -> tuple[bool, str | None]:
    """Validate that a sanitized event is safe to persist.

    Delegates to the schema validator after confirming the event carries no
    sentinel leakage in forbidden fields.
    """
    if not isinstance(event, dict):
        return False, "event is not a JSON object"
    ok, reason = validate_canonical_event(event)
    if not ok:
        return False, reason
    # Defense-in-depth: forbidden fields must be absent or redacted.
    for key, value in event.items():
        if _is_forbidden_field(key) and value not in (None, REDACTED_SENTINEL):
            return False, f"forbidden field not redacted: {key}"
    return True, None


# ---------------------------------------------------------------------------
# 6. Helpers
# ---------------------------------------------------------------------------


def _minimal_safe_event(event_type: str | None = None) -> dict[str, Any]:
    """Return the minimal safe canonical event used when sanitization fails.

    This is a degenerate event that still validates against the schema so the
    store writer can persist a breadcrumb without ever raising. ``sequence`` is
    0 (the schema requires a non-negative integer); the store writer stamps the
    real monotonic sequence on append.
    """
    return {
        "eventId": "00000000-0000-0000-0000-000000000000",
        "sequence": 0,
        "createdAt": "1970-01-01T00:00:00+00:00",
        "eventType": event_type or "audit_sanitization_fallback",
        "auditKind": "internal",
        "schemaVersion": AUDIT_SCHEMA_VERSION,
        "summary": {},
        "safeMetadata": {
            "sanitization": "fallback",
        },
        "redactionApplied": True,
    }
