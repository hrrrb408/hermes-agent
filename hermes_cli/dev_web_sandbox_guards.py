"""Phase 3H Dev-only Sandbox Proof Skeleton — Guards (Block 2).

Pure, stdlib-only, side-effect-free evaluators for the three denial surfaces a
dev-only sandbox proof must enforce:

  - **Filesystem boundary** — allow only explicit dev-safe temp / fixture
    roots; deny ``~/.hermes``, production ``state.db``, traversal escape,
    symlink escape, the home fallback, unknown write locations, and any
    runtime-store / plugin-store write.
  - **Network deny** — every external network target is denied by *intent*
    (string / request-intent level). No socket, no DNS, no ``requests`` /
    ``httpx`` / ``aiohttp``, no ``ping``. Even a request for the
    ``network.request`` capability is denied.
  - **Secrets unavailable / redaction** — never reads the env, ``.env``, real
    API keys, ``Authorization`` / ``Bearer`` headers, ``sk-`` / ``ghp_`` /
    ``xox`` tokens, or PEM private keys. A standalone redaction utility masks
    every known secret shape **and** production-path-like values.

Hard guarantees (frozen, see docs/webui/phase-3h-sandbox-proof-planning.md):

  - Pure / deterministic / stdlib-only. No ``importlib`` / ``__import__`` /
    ``subprocess`` / ``shell`` / socket / DNS / live HTTP.
  - **Never** opens, reads, or writes ``~/.hermes`` or any production
    ``state.db``. Production is referenced only as a denial target string.
  - **Never** performs a network call of any kind. Network denial is a pure
    string/intent decision.
  - **Never** reads the environment for a real secret. ``os.environ`` is not
    consulted; secret *requests* are denied and secret *values* are redacted
    from caller-supplied strings only.

Phase: 3H — Dev-only Sandbox Proof Skeleton
Status: implemented (guards). No plugin execution, no dynamic loading, no
        external network, no real secret read, no new route, no production
        access.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import urlsplit

from hermes_cli.dev_web_safety_baseline import (
    evaluate_path_safety,
    is_production_home,
    is_production_state_db,
)

REDACTED_VALUE = "[REDACTED]"
SANDBOX_GUARD_AUDIT_SOURCE = "dev_web_sandbox_guards"

# ---------------------------------------------------------------------------
# 1. Filesystem boundary guard
# ---------------------------------------------------------------------------

#: Reasons the filesystem guard may emit. Each is a stable, grep-able token.
FS_GUARD_REASONS: frozenset[str] = frozenset(
    {
        "forbidden_production_home",
        "forbidden_production_database",
        "forbidden_absolute_production_path",
        "forbidden_runtime_store_name",
        "path_traversal_escape",
        "symlink_escape",
        "home_directory_fallback",
        "write_outside_allowed_root",
        "unknown_write_location",
        "invalid_path",
    }
)


@dataclass(frozen=True, slots=True)
class FilesystemDecision:
    """Value-free filesystem decision. Never carries file contents."""

    path_redacted: str
    allowed: bool
    reasons: tuple[str, ...] = ()
    inside_allowed_root: bool = False
    is_write: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "path": self.path_redacted,
            "allowed": self.allowed,
            "reasons": list(self.reasons),
            "insideAllowedRoot": self.inside_allowed_root,
            "isWrite": self.is_write,
            "redactionApplied": True,
        }


def _redact_path_for_audit(candidate: Any) -> str:
    """Render a path for an audit record. Production-like paths are masked.

    Never returns a raw production path. A path that resolves into the
    production home or a production database is replaced wholesale; an
    otherwise-safe path is shown verbatim (it is a dev temp / fixture path).
    """
    if not isinstance(candidate, (str, os.PathLike)):
        return REDACTED_VALUE if candidate is not None else ""
    text = os.path.expanduser(str(candidate))
    if is_production_home(text) or is_production_state_db(text) or "/.hermes" in text:
        return REDACTED_VALUE
    if "state.db" in text.lower():
        return REDACTED_VALUE
    return text


def evaluate_filesystem_path(
    candidate: Any,
    *,
    allowed_roots: Iterable[Any] = (),
    allow_write: bool = False,
) -> FilesystemDecision:
    """Evaluate a filesystem access request. Default-deny outside safe roots.

    Delegates the core denial logic to
    :func:`evaluate_path_safety` (which never opens the target) and layers two
    sandbox-specific guards on top:

      - **home-directory fallback** — a request for the user home directory
        itself (``~`` / ``~/.hermes`` / ``/Users/<user>``) is denied, because a
        dev-only skeleton never reads the home tree.
      - **unknown write location** — a write with no allowed root supplied is
        denied even if the path is otherwise benign.
    """
    reasons: list[str] = []
    inside = False

    if not isinstance(candidate, (str, os.PathLike)):
        return FilesystemDecision(
            path_redacted=REDACTED_VALUE,
            allowed=False,
            reasons=("invalid_path",),
            is_write=allow_write,
        )

    text = os.path.expanduser(str(candidate))

    # Home-directory fallback: deny a bare home or the user's home tree.
    home = os.path.expanduser("~")
    if text == "~" or text == home or text.rstrip("/") == home:
        reasons.append("home_directory_fallback")

    decision = evaluate_path_safety(text, allowed_roots=allowed_roots, allow_write=allow_write)
    for reason in decision["reasons"]:
        if reason not in reasons:
            reasons.append(reason)

    # Compute "inside an allowed root" from the normalized path without
    # re-opening anything.
    roots = [os.path.expanduser(str(r)) for r in allowed_roots if r]
    norm = decision["normalized"]
    inside = any(
        norm == _normalize_for_compare(r) or norm.startswith(_normalize_for_compare(r).rstrip("/") + "/")
        for r in roots
    ) if roots else False

    # Unknown write location: a write that survived the base evaluator but has
    # no allowed root at all (the base evaluator flags this as
    # write_outside_allowed_root already; this is a defensive duplicate label
    # so the audit record is unambiguous).
    if allow_write and not roots and "write_outside_allowed_root" not in reasons:
        reasons.append("unknown_write_location")

    allowed = len(reasons) == 0
    return FilesystemDecision(
        path_redacted=_redact_path_for_audit(candidate) if allowed else REDACTED_VALUE,
        allowed=allowed,
        reasons=tuple(reasons),
        inside_allowed_root=inside,
        is_write=allow_write,
    )


def _normalize_for_compare(text: str) -> str:
    """Lexical normalization for comparison (mirrors safety_baseline)."""
    parts: list[str] = []
    is_abs = text.startswith("/")
    for part in text.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    if not parts:
        return "/" if is_abs else "."
    joined = "/".join(parts)
    return "/" + joined if is_abs else joined


# ---------------------------------------------------------------------------
# 2. Network deny guard
# ---------------------------------------------------------------------------

#: Reasons the network guard may emit.
NETWORK_GUARD_REASONS: frozenset[str] = frozenset(
    {
        "network_request_capability_denied",
        "external_url_denied",
        "provider_endpoint_denied",
        "remote_registry_denied",
        "marketplace_denied",
        "external_plugin_fetch_denied",
        "telemetry_callback_denied",
        "host_like_target_denied",
        "private_loopback_denied",
        "invalid_network_target",
    }
)

#: Substrings that mark a network target as a known forbidden intent. Matched
#: case-insensitively against the raw target string. This is a pure intent
#: classifier — no host is ever contacted.
_NETWORK_INTENT_MARKERS: tuple[tuple[str, str], ...] = (
    ("://", "external_url_denied"),
    ("api.openai.com", "provider_endpoint_denied"),
    ("api.anthropic.com", "provider_endpoint_denied"),
    ("registry", "remote_registry_denied"),
    ("marketplace", "marketplace_denied"),
    ("store", "marketplace_denied"),
    ("/install", "external_plugin_fetch_denied"),
    ("download", "external_plugin_fetch_denied"),
    ("telemetry", "telemetry_callback_denied"),
    ("callback", "telemetry_callback_denied"),
    ("webhook", "telemetry_callback_denied"),
    (".com", "host_like_target_denied"),
    (".io", "host_like_target_denied"),
    (".org", "host_like_target_denied"),
    (".net", "host_like_target_denied"),
    ("localhost", "private_loopback_denied"),
    ("127.0.0.1", "private_loopback_denied"),
    ("0.0.0.0", "private_loopback_denied"),
)


@dataclass(frozen=True, slots=True)
class NetworkDecision:
    """Value-free network decision. Never carries a resolved host or URL."""

    target_redacted: str
    allowed: bool
    reasons: tuple[str, ...] = ()

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "target": self.target_redacted,
            "allowed": self.allowed,
            "reasons": list(self.reasons),
            "redactionApplied": True,
        }


def evaluate_network_target(target: Any, *, capability_requested: bool = False) -> NetworkDecision:
    """Evaluate a network target. **Always denies** for a dev-only sandbox.

    A sandbox proof has no network surface. Any non-empty target is denied with
    the most specific intent reason; an empty target is a no-op (allowed) **only
    when no network capability was requested**. Requesting the
    ``network.request`` capability is denied even with an empty target.
    """
    if capability_requested:
        if not isinstance(target, (str,)) or not target.strip():
            return NetworkDecision(
                target_redacted="",
                allowed=False,
                reasons=("network_request_capability_denied",),
            )
        return NetworkDecision(
            target_redacted=REDACTED_VALUE,
            allowed=False,
            reasons=_network_reasons(target),
        )

    if not isinstance(target, str) or not target.strip():
        # Empty target with no network capability requested → no-op, allowed.
        return NetworkDecision(target_redacted="", allowed=True, reasons=())

    return NetworkDecision(
        target_redacted=REDACTED_VALUE,
        allowed=False,
        reasons=_network_reasons(target),
    )


def _network_reasons(target: str) -> tuple[str, ...]:
    reasons: list[str] = ["network_request_capability_denied"]
    lowered = target.lower()
    for marker, reason in _NETWORK_INTENT_MARKERS:
        if marker in lowered and reason not in reasons:
            reasons.append(reason)
    # A URL with a scheme is unambiguously external.
    try:
        parts = urlsplit(target.strip())
    except ValueError:
        parts = None
    if parts is not None and parts.scheme and parts.netloc:
        if "external_url_denied" not in reasons:
            reasons.append("external_url_denied")
    return tuple(reasons)


# ---------------------------------------------------------------------------
# 3. Secrets unavailable / redaction guard
# ---------------------------------------------------------------------------

#: Reasons the secrets guard may emit.
SECRET_GUARD_REASONS: frozenset[str] = frozenset(
    {
        "secret_request_denied",
        "secret_value_detected",
        "api_key_label_denied",
        "authorization_header_denied",
        "bearer_token_denied",
        "private_key_denied",
        "invalid_secret_target",
    }
)

#: Secret-bearing field-name stems (mirrors the Phase 3B redactor, widened).
_SECRET_FIELD_STEMS: tuple[str, ...] = (
    "token", "secret", "password", "auth", "apikey", "api_key", "privatekey",
    "private_key", "credential",
)

#: Secret value patterns. Frozen and widened for the sandbox proof — these are
#: the *only* shapes a redaction test may rely on.
_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"),
    re.compile(r"ghp_[A-Za-z0-9]{8,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
)

#: Production-path-like value patterns — redacted as if they were secrets.
_FORBIDDEN_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"/Users/[^/]+/\.hermes", re.IGNORECASE),
    re.compile(r"\bstate\.db\b", re.IGNORECASE),
    re.compile(r"\.hermes/", re.IGNORECASE),
)

_MAX_REDACT_DEPTH = 8


@dataclass(frozen=True, slots=True)
class SecretDecision:
    """Value-free secret decision. Never carries a key value."""

    secret_name_redacted: str
    allowed: bool
    reasons: tuple[str, ...] = ()

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "secretName": self.secret_name_redacted,
            "allowed": self.allowed,
            "reasons": list(self.reasons),
            "keyValue": "never",
            "redactionApplied": True,
        }


def _is_secret_bearing_name(name: Any) -> bool:
    if not isinstance(name, str):
        return False
    normalized = name.strip().lower().replace("-", "").replace("_", "")
    return any(stem.replace("_", "") in normalized for stem in _SECRET_FIELD_STEMS)


def detect_secret_in_string(value: Any) -> tuple[bool, str]:
    """Return ``(detected, reason)`` for a secret / forbidden value in a string.

    Detects ``sk-`` / ``ghp_`` / ``xox`` tokens, ``Bearer …`` /
    ``Authorization: …`` headers, PEM private-key blocks, and production
    path-like values (``~/.hermes`` / ``state.db``). Never raises.
    """
    if not isinstance(value, str):
        return False, ""
    for pattern in _SECRET_VALUE_PATTERNS:
        if pattern.search(value):
            return True, "secret_value_detected"
    for pattern in _FORBIDDEN_VALUE_PATTERNS:
        if pattern.search(value):
            return True, "secret_value_detected"
    return False, ""


def evaluate_secret_request(secret_name: Any) -> SecretDecision:
    """Evaluate a secret read request. **Always denies** for a dev-only sandbox.

    A sandbox proof has no secret surface. Any request to read a secret
    (named or empty) is denied; the named slot is redacted in the audit record.
    """
    reasons: list[str] = ["secret_request_denied"]
    if not isinstance(secret_name, str) or not secret_name.strip():
        return SecretDecision(
            secret_name_redacted="",
            allowed=False,
            reasons=tuple(reasons),
        )
    if _is_secret_bearing_name(secret_name):
        reasons.append("api_key_label_denied")
    lowered = secret_name.lower()
    if "authorization" in lowered:
        reasons.append("authorization_header_denied")
    if "bearer" in lowered:
        reasons.append("bearer_token_denied")
    if "private" in lowered and "key" in lowered:
        reasons.append("private_key_denied")
    return SecretDecision(
        secret_name_redacted=REDACTED_VALUE,
        allowed=False,
        reasons=tuple(reasons),
    )


def _redact_scalar(value: str) -> str:
    detected, _ = detect_secret_in_string(value)
    return REDACTED_VALUE if detected else value


def redact_sandbox_text(value: Any) -> str:
    """Redact any secret / production-path value in a scalar string.

    Returns the redacted string. Non-string input is coerced to a string first;
    a detected secret collapses the whole value to ``[REDACTED]``. Never raises.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return _redact_scalar(value)


def redact_sandbox_payload(payload: Any, *, depth: int = 0) -> Any:
    """Recursively redact a payload (dict / list / scalar) for an audit record.

    Replaces secret values and secret-bearing-field string values with
    ``[REDACTED]``, bounds nesting depth at 8, and collapses non-JSON-native
    values (callables / objects) to a placeholder — never their repr. Mirrors
    the Phase 3B redactor's token-count precision: a bare ``int``/``float``/
    ``bool``/``None`` under a secret-bearing name is preserved (a count, not a
    secret).
    """
    if depth > _MAX_REDACT_DEPTH:
        return None
    if isinstance(payload, str):
        return _redact_scalar(payload)
    if isinstance(payload, (int, float, bool)) or payload is None:
        return payload
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, val in payload.items():
            if _is_secret_bearing_name(key) and isinstance(val, str) and val:
                out[str(key)] = REDACTED_VALUE
                continue
            out[str(key)] = redact_sandbox_payload(val, depth=depth + 1)
        return out
    if isinstance(payload, (list, tuple)):
        return [redact_sandbox_payload(v, depth=depth + 1) for v in payload]
    # Non-JSON-native (callables, objects) → placeholder, never repr.
    return "<non_json_value>"


def contains_secret(payload: Any, *, depth: int = 0) -> bool:
    """Recursively sweep a payload for any secret / forbidden-path value.

    A value already collapsed to :data:`REDACTED_VALUE` is treated as safe by
    construction (it is the redaction placeholder, not a secret) — this lets a
    final defensive sweep run over an already-redacted record without false
    positives that would otherwise flag the placeholder under a secret-bearing
    field name.
    """
    if depth > _MAX_REDACT_DEPTH:
        return False
    if isinstance(payload, str):
        if payload == REDACTED_VALUE:
            return False
        detected, _ = detect_secret_in_string(payload)
        return detected
    if isinstance(payload, dict):
        for key, val in payload.items():
            if _is_secret_bearing_name(key):
                if isinstance(val, str):
                    if val and val != REDACTED_VALUE:
                        return True
                elif isinstance(val, (dict, list, tuple)) and contains_secret(val, depth=depth + 1):
                    return True
            elif contains_secret(val, depth=depth + 1):
                return True
        return False
    if isinstance(payload, (list, tuple)):
        return any(contains_secret(v, depth=depth + 1) for v in payload)
    return False


# Place this import after the helpers so the module reads top-down; re-import
# is cheap and keeps the public surface stable.


__all__ = [
    "REDACTED_VALUE",
    "SANDBOX_GUARD_AUDIT_SOURCE",
    "FS_GUARD_REASONS",
    "FilesystemDecision",
    "evaluate_filesystem_path",
    "NETWORK_GUARD_REASONS",
    "NetworkDecision",
    "evaluate_network_target",
    "SECRET_GUARD_REASONS",
    "SecretDecision",
    "detect_secret_in_string",
    "evaluate_secret_request",
    "redact_sandbox_text",
    "redact_sandbox_payload",
    "contains_secret",
]
