"""Phase 3B Real Provider Policy — Gating, Allowlist, Retry Classification.

The single policy surface for the real-provider boundary:

  1. ``evaluate_real_provider_gating`` — the fine-grained enablement gate that
     maps a config state to a frozen-catalogue ``blocked_provider_*`` reason.
     Real mode is eligible only when EVERY condition holds; any failure fails
     closed with a precise reason and no network call.
  2. The read-only tool-call allowlist (reuses the Phase 2A ``STATIC_ALLOWLIST``
     unchanged) + the forbidden write / shell / db / external / production /
     plugin-load names, each mapping to a precise blocked reason.
  3. ``is_safe_transient_failure`` — the retry decision (safe-transient only;
     auth / policy / budget / secret / oversize never retry).

Phase: 3B — Real Provider Read-only Controlled Integration
Status: policy implemented
"""

from __future__ import annotations

from typing import Any, Mapping

from hermes_cli.dev_web_provider_config import (
    ProviderRealConfig,
    _IMPLEMENTED_PROVIDER_NAMES,
)
from hermes_cli.dev_web_provider_request import (
    BLOCKED_PROVIDER_API_KEY_MISSING,
    BLOCKED_PROVIDER_NOT_DEV_HOME,
    BLOCKED_PROVIDER_PRODUCTION_GATE_DRIFT,
    _has_provider_api_key,
    _is_dev_home,
    _production_gate_passed,
)

# ---------------------------------------------------------------------------
# 1. Frozen blocked-reason catalogue
# ---------------------------------------------------------------------------

BLOCKED_PROVIDER_REAL_NOT_ENABLED = "blocked_provider_real_not_enabled"
BLOCKED_PROVIDER_API_DISABLED = "blocked_provider_api_disabled"
BLOCKED_PROVIDER_BASE_URL_NOT_ALLOWED = "blocked_provider_base_url_not_allowed"
BLOCKED_PROVIDER_API_KEY_MISSING = BLOCKED_PROVIDER_API_KEY_MISSING
BLOCKED_PROVIDER_NAME_NOT_SUPPORTED = "blocked_provider_name_not_supported"
BLOCKED_PROVIDER_MODEL_NOT_ALLOWED = "blocked_provider_model_not_allowed"
BLOCKED_PROVIDER_NOT_DEV_HOME = BLOCKED_PROVIDER_NOT_DEV_HOME
BLOCKED_PROVIDER_PRODUCTION_GATE_DRIFT = BLOCKED_PROVIDER_PRODUCTION_GATE_DRIFT
BLOCKED_PROVIDER_TIMEOUT_INVALID = "blocked_provider_timeout_invalid"
BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED = "blocked_provider_rate_limit_exceeded"
BLOCKED_PROVIDER_BUDGET_EXCEEDED = "blocked_provider_budget_exceeded"
BLOCKED_PROVIDER_RESPONSE_TOO_LARGE = "blocked_provider_response_too_large"
BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED = "blocked_provider_tool_call_not_allowed"
BLOCKED_PROVIDER_WRITE_NOT_ALLOWED = "blocked_provider_write_not_allowed"
BLOCKED_PROVIDER_EXTERNAL_URL_NOT_ALLOWED = "blocked_provider_external_url_not_allowed"
BLOCKED_PROVIDER_SECRET_DETECTED = "blocked_provider_secret_detected"
BLOCKED_PROVIDER_AUTH_FAILED = "blocked_provider_auth_failed"
BLOCKED_PROVIDER_MALFORMED_RESPONSE = "blocked_provider_malformed_response"
BLOCKED_PROVIDER_SCHEMA_MISMATCH = "blocked_provider_schema_mismatch"
BLOCKED_PROVIDER_NETWORK_UNAVAILABLE = "blocked_provider_network_unavailable"
BLOCKED_PROVIDER_RETRY_EXHAUSTED = "blocked_provider_retry_exhausted"


# ---------------------------------------------------------------------------
# 2. Enablement gating (fine-grained, frozen-catalogue reasons)
# ---------------------------------------------------------------------------


def evaluate_real_provider_gating(
    config: ProviderRealConfig,
    *,
    production_gate_override: bool | None = None,
) -> tuple[bool, str | None]:
    """Return (eligible, blocked_reason) for a real round-trip.

    Evaluation order (first failure wins; all fail closed with no network call):

      1. mode == real            else blocked_provider_real_not_enabled
      2. api_enabled             else blocked_provider_api_disabled
      3. provider name implemented else blocked_provider_name_not_supported
      4. api key present         else blocked_provider_api_key_missing
      5. dev home (not ~/.hermes) else blocked_provider_not_dev_home
      6. production PID gate     else blocked_provider_production_gate_drift
      7. base URL allowlisted    else blocked_provider_base_url_not_allowed
      8. model allowlisted       else blocked_provider_model_not_allowed
      9. timeout in bounds       else blocked_provider_timeout_invalid
    """
    if config.provider_mode != "real":
        return False, BLOCKED_PROVIDER_REAL_NOT_ENABLED
    if not config.api_enabled:
        return False, BLOCKED_PROVIDER_API_DISABLED
    if config.provider_name not in _IMPLEMENTED_PROVIDER_NAMES:
        return False, BLOCKED_PROVIDER_NAME_NOT_SUPPORTED
    # API-key presence is re-checked live (the config snapshot may be stale).
    if not (_has_provider_api_key() or config.api_key_source_detail == "env_present"):
        return False, BLOCKED_PROVIDER_API_KEY_MISSING
    if not (config.is_dev_home and _is_dev_home()):
        return False, BLOCKED_PROVIDER_NOT_DEV_HOME
    if production_gate_override is None:
        gate_ok = _production_gate_passed()
    else:
        gate_ok = production_gate_override
    if not gate_ok:
        return False, BLOCKED_PROVIDER_PRODUCTION_GATE_DRIFT
    if not config.base_url_allowed:
        return False, BLOCKED_PROVIDER_BASE_URL_NOT_ALLOWED
    if not config.model_allowed:
        return False, BLOCKED_PROVIDER_MODEL_NOT_ALLOWED
    if config.timeout_seconds < 1:
        return False, BLOCKED_PROVIDER_TIMEOUT_INVALID
    return True, None


# ---------------------------------------------------------------------------
# 3. Read-only tool-call allowlist (reuses STATIC_ALLOWLIST unchanged)
# ---------------------------------------------------------------------------

# Names that are PERMANENTLY forbidden for a provider tool call, each mapping to
# a precise blocked reason. These are defense-in-depth: none are in the read-only
# allowlist anyway, but the provider is untrusted input.
_FORBIDDEN_TOOL_REASONS: dict[str, str] = {
    "dev_sandbox_file_write": BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
    "dev_sandbox_file_append": BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
    "dev_sandbox_file_patch": BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
    "dev_sandbox_file_readback": BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    "dev_sandbox_rollback_execute": BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    "write_file": BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
    "patch": BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
    "memory": BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
    "memory_add": BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
    "memory_update": BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
    "todo": BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
    "skill_manage": BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
    "send_message": BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    "terminal": BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    "process": BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    "execute_code": BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    "delegate_task": BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    "cronjob": BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    "image_generate": BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    "shell": BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    "database": BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    "external_http": BLOCKED_PROVIDER_EXTERNAL_URL_NOT_ALLOWED,
    "production_operation": BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    "plugin_dynamic_load": BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
}


def get_read_only_tool_allowlist() -> frozenset[str]:
    """Return the Phase 2A STATIC_ALLOWLIST (the only tools a provider may call)."""
    from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

    return STATIC_ALLOWLIST


def classify_provider_tool_call(
    tool_id: Any, arguments: Mapping[str, Any] | Any,
) -> tuple[bool, str | None]:
    """Classify a provider-requested tool call against the read-only boundary.

    Returns (allowed, blocked_reason). Only read-only allowlisted tools pass;
    forbidden names get their precise reason; everything else is rejected as
    ``blocked_provider_tool_call_not_allowed``.
    """
    if not isinstance(tool_id, str) or not tool_id.strip():
        return False, BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED
    allowlist = get_read_only_tool_allowlist()
    if tool_id in allowlist:
        return True, None
    if tool_id in _FORBIDDEN_TOOL_REASONS:
        return False, _FORBIDDEN_TOOL_REASONS[tool_id]
    return False, BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED


# ---------------------------------------------------------------------------
# 4. Retry classification (safe-transient only)
# ---------------------------------------------------------------------------

# These reasons / statuses are SAFE-TRANSIENT and MAY be retried (subject to the
# cap). Everything else short-circuits (auth / policy / budget / secret / oversize).
_SAFE_TRANSIENT_REASONS: frozenset[str] = frozenset(
    {
        BLOCKED_PROVIDER_NETWORK_UNAVAILABLE,
        BLOCKED_PROVIDER_RETRY_EXHAUSTED,
    }
)
_SAFE_TRANSIENT_HTTP_STATUSES: frozenset[int] = frozenset({408, 425, 500, 502, 503, 504})


def is_safe_transient_failure(*, http_status: int | None, blocked_reason: str | None) -> bool:
    """True only for a safe-transient failure that MAY be retried.

    NEVER true for: auth failure (401/403), policy-blocked, budget exceeded,
    rate-limit, response too large, secret detected, malformed response, schema
    mismatch. A retry storm is structurally impossible: non-retryable classes
    short-circuit immediately.
    """
    if blocked_reason is not None and blocked_reason in _SAFE_TRANSIENT_REASONS:
        return True
    if blocked_reason is not None:
        return False
    if http_status is None:
        return False
    return http_status in _SAFE_TRANSIENT_HTTP_STATUSES


def is_auth_failure(http_status: int | None) -> bool:
    """401 / 403 → auth failure (never retried; never logged with the key)."""
    return http_status in (401, 403)


def classify_http_failure(http_status: int | None) -> str:
    """Map an HTTP status to a terminal blocked reason."""
    if is_auth_failure(http_status):
        return BLOCKED_PROVIDER_AUTH_FAILED
    if http_status == 429:
        return BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED
    if http_status is not None and 400 <= http_status < 500:
        return BLOCKED_PROVIDER_SCHEMA_MISMATCH
    if http_status is not None and http_status >= 500:
        return BLOCKED_PROVIDER_NETWORK_UNAVAILABLE
    return BLOCKED_PROVIDER_NETWORK_UNAVAILABLE


__all__ = [
    "BLOCKED_PROVIDER_REAL_NOT_ENABLED",
    "BLOCKED_PROVIDER_API_DISABLED",
    "BLOCKED_PROVIDER_BASE_URL_NOT_ALLOWED",
    "BLOCKED_PROVIDER_API_KEY_MISSING",
    "BLOCKED_PROVIDER_NAME_NOT_SUPPORTED",
    "BLOCKED_PROVIDER_MODEL_NOT_ALLOWED",
    "BLOCKED_PROVIDER_NOT_DEV_HOME",
    "BLOCKED_PROVIDER_PRODUCTION_GATE_DRIFT",
    "BLOCKED_PROVIDER_TIMEOUT_INVALID",
    "BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED",
    "BLOCKED_PROVIDER_BUDGET_EXCEEDED",
    "BLOCKED_PROVIDER_RESPONSE_TOO_LARGE",
    "BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED",
    "BLOCKED_PROVIDER_WRITE_NOT_ALLOWED",
    "BLOCKED_PROVIDER_EXTERNAL_URL_NOT_ALLOWED",
    "BLOCKED_PROVIDER_SECRET_DETECTED",
    "BLOCKED_PROVIDER_AUTH_FAILED",
    "BLOCKED_PROVIDER_MALFORMED_RESPONSE",
    "BLOCKED_PROVIDER_SCHEMA_MISMATCH",
    "BLOCKED_PROVIDER_NETWORK_UNAVAILABLE",
    "BLOCKED_PROVIDER_RETRY_EXHAUSTED",
    "evaluate_real_provider_gating",
    "get_read_only_tool_allowlist",
    "classify_provider_tool_call",
    "is_safe_transient_failure",
    "is_auth_failure",
    "classify_http_failure",
]
