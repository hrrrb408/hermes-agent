"""Handler Lookup for the Hermes Dev WebUI Tool Execute Gate.

This module implements minimal safe handler descriptor lookup for the execute
gate stack.  It resolves safe handler metadata for allowlisted tools and
returns a handler descriptor with no executable references.

Architecture constraints:
  - stdlib only (no third-party imports)
  - no provider imports, no tool handler imports, no dispatch imports
  - no network IO, no filesystem mutation, no runtime state mutation
  - no STATIC_ALLOWLIST mutation
  - deterministic, JSON-serializable output
  - never stores raw confirmationToken
  - never stores full tokenHash
  - never stores raw arguments
  - never stores secrets
  - never calls handler / dispatch / provider
  - handler lookup success does NOT imply execution
  - handler existence is NOT permission
  - handler descriptor is NOT permission
  - STATIC_ALLOWLIST remains the permission boundary

Phase: 1G-04-26 — Handler Lookup Minimal Implementation
Status: Safe metadata lookup implemented, execute still blocked-only
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

HANDLER_LOOKUP_ID_PREFIX = "hl_"
HANDLER_LOOKUP_SCHEMA_VERSION = 1
HANDLER_DESCRIPTOR_VERSION = 1

HANDLER_LOOKUP_STATUS_FOUND = "found"
HANDLER_LOOKUP_STATUS_NOT_FOUND = "not_found"
HANDLER_LOOKUP_STATUS_BLOCKED = "blocked"

# ID random bytes
_ID_RANDOM_BYTES = 16  # 128 bits of randomness

# Safe metadata source: minimal static descriptor mapping for allowlisted tools
# Only covers tools in STATIC_ALLOWLIST. Handler existence is NOT permission.
#
# Phase 2A: the five read-only inspection tools each get a safe-metadata
# descriptor. They are Dev-WebUI-local bounded handlers (NOT registered Hermes
# agent tools) resolved by dispatch_read_only_tool in
# dev_web_read_only_tool_handlers.py. The registryKey MUST equal the
# canonicalName (dev_web_tool_dispatch.py enforces this invariant). All
# permission flags remain False — handler existence is necessary-but-not-
# sufficient; only STATIC_ALLOWLIST membership grants execution eligibility.
_SAFE_HANDLER_DESCRIPTORS: dict[str, dict[str, Any]] = {
    "clarify": {
        "canonicalName": "clarify",
        "handlerId": "handler_clarify",
        "registryKey": "clarify",
        "moduleName": "builtin.safe_metadata_only",
        "callableName": "clarify",
        "riskTier": "R0",
        "allowlisted": True,
        "dispatchAllowed": False,
        "executionAllowed": False,
        "providerSchemaAllowed": False,
        "sideEffectFreeLookup": True,
    },
    "tool_policy_read": {
        "canonicalName": "tool_policy_read",
        "handlerId": "handler_tool_policy_read",
        "registryKey": "tool_policy_read",
        "moduleName": "builtin.safe_metadata_only",
        "callableName": "tool_policy_read",
        "riskTier": "R0",
        "allowlisted": True,
        "dispatchAllowed": False,
        "executionAllowed": False,
        "providerSchemaAllowed": False,
        "sideEffectFreeLookup": True,
    },
    "route_governance_read": {
        "canonicalName": "route_governance_read",
        "handlerId": "handler_route_governance_read",
        "registryKey": "route_governance_read",
        "moduleName": "builtin.safe_metadata_only",
        "callableName": "route_governance_read",
        "riskTier": "R0",
        "allowlisted": True,
        "dispatchAllowed": False,
        "executionAllowed": False,
        "providerSchemaAllowed": False,
        "sideEffectFreeLookup": True,
    },
    "audit_events_read": {
        "canonicalName": "audit_events_read",
        "handlerId": "handler_audit_events_read",
        "registryKey": "audit_events_read",
        "moduleName": "builtin.safe_metadata_only",
        "callableName": "audit_events_read",
        "riskTier": "R1",
        "allowlisted": True,
        "dispatchAllowed": False,
        "executionAllowed": False,
        "providerSchemaAllowed": False,
        "sideEffectFreeLookup": True,
    },
    "dev_environment_read": {
        "canonicalName": "dev_environment_read",
        "handlerId": "handler_dev_environment_read",
        "registryKey": "dev_environment_read",
        "moduleName": "builtin.safe_metadata_only",
        "callableName": "dev_environment_read",
        "riskTier": "R1",
        "allowlisted": True,
        "dispatchAllowed": False,
        "executionAllowed": False,
        "providerSchemaAllowed": False,
        "sideEffectFreeLookup": True,
    },
    "release_status_read": {
        "canonicalName": "release_status_read",
        "handlerId": "handler_release_status_read",
        "registryKey": "release_status_read",
        "moduleName": "builtin.safe_metadata_only",
        "callableName": "release_status_read",
        "riskTier": "R1",
        "allowlisted": True,
        "dispatchAllowed": False,
        "executionAllowed": False,
        "providerSchemaAllowed": False,
        "sideEffectFreeLookup": True,
    },
}


# ---------------------------------------------------------------------------
# 2. Error codes / decisions
# ---------------------------------------------------------------------------

ERROR_HANDLER_LOOKUP_NOT_ENABLED = "handler_lookup_not_enabled"
ERROR_HANDLER_LOOKUP_UNAVAILABLE = "handler_lookup_unavailable"
ERROR_HANDLER_LOOKUP_NOT_FOUND = "handler_lookup_not_found"
ERROR_HANDLER_LOOKUP_NOT_ALLOWLISTED = "handler_lookup_not_allowlisted"
ERROR_HANDLER_LOOKUP_REGISTRY_UNAVAILABLE = "handler_lookup_registry_unavailable"
ERROR_HANDLER_LOOKUP_DESCRIPTOR_INVALID = "handler_lookup_descriptor_invalid"
ERROR_HANDLER_LOOKUP_SIDE_EFFECT_RISK = "handler_lookup_side_effect_risk"
ERROR_HANDLER_LOOKUP_POLICY_MISMATCH = "handler_lookup_policy_mismatch"
ERROR_HANDLER_LOOKUP_WRITTEN_BUT_DISPATCH_NOT_ENABLED = (
    "handler_lookup_written_but_dispatch_not_enabled"
)
ERROR_DISPATCH_NOT_ENABLED = "dispatch_not_enabled"

DECISION_BLOCKED_HANDLER_LOOKUP_UNAVAILABLE = "blocked_handler_lookup_unavailable"
DECISION_BLOCKED_HANDLER_LOOKUP_NOT_FOUND = "blocked_handler_lookup_not_found"
DECISION_BLOCKED_HANDLER_LOOKUP_NOT_ALLOWLISTED = "blocked_handler_lookup_not_allowlisted"
DECISION_BLOCKED_HANDLER_LOOKUP_REGISTRY_UNAVAILABLE = (
    "blocked_handler_lookup_registry_unavailable"
)
DECISION_BLOCKED_HANDLER_LOOKUP_DESCRIPTOR_INVALID = (
    "blocked_handler_lookup_descriptor_invalid"
)
DECISION_BLOCKED_HANDLER_LOOKUP_SIDE_EFFECT_RISK = (
    "blocked_handler_lookup_side_effect_risk"
)
DECISION_BLOCKED_HANDLER_LOOKUP_POLICY_MISMATCH = (
    "blocked_handler_lookup_policy_mismatch"
)
DECISION_BLOCKED_DISPATCH_NOT_ENABLED = "blocked_dispatch_not_enabled"


# ---------------------------------------------------------------------------
# 3. Required descriptor fields
# ---------------------------------------------------------------------------

_REQUIRED_DESCRIPTOR_FIELDS: frozenset[str] = frozenset(
    {
        "canonicalName",
        "handlerId",
        "registryKey",
        "moduleName",
        "callableName",
        "riskTier",
        "allowlisted",
        "dispatchAllowed",
        "executionAllowed",
        "providerSchemaAllowed",
        "sideEffectFreeLookup",
    }
)


# ---------------------------------------------------------------------------
# 4. Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HandlerLookupResult:
    """Immutable result of handler descriptor lookup."""

    found: bool
    handler_lookup_id: str | None
    handler_lookup_status: str
    handler_descriptor: dict[str, Any] | None
    error_code: str | None
    decision: str | None
    gate: str | None
    created_at: str | None = None
    safe_summary: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 5. Internal helpers
# ---------------------------------------------------------------------------


def _handler_lookup_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def _generate_handler_lookup_id() -> str:
    """Generate a unique handler lookup correlation ID.

    Format: ``hl_`` + base64url-safe random string.
    The ID is not an authorization credential — it is only for correlation.
    It never contains raw token, full tokenHash, or secrets.
    """
    return f"{HANDLER_LOOKUP_ID_PREFIX}{secrets.token_urlsafe(_ID_RANDOM_BYTES)}"


def _build_side_effect_flags() -> dict[str, bool]:
    """Build side-effect flags — all always false."""
    return {
        "executionAllowed": False,
        "dispatchAllowed": False,
        "providerSchemaAllowed": False,
        "toolHandlerCalled": False,
        "providerApiCalled": False,
        "executionStarted": False,
    }


def _fail_closed(
    *,
    error_code: str,
    decision: str,
    handler_lookup_status: str = HANDLER_LOOKUP_STATUS_BLOCKED,
    gate: str | None = None,
) -> HandlerLookupResult:
    """Return a fail-closed lookup result — never an unhandled exception."""
    return HandlerLookupResult(
        found=False,
        handler_lookup_id=None,
        handler_lookup_status=handler_lookup_status,
        handler_descriptor=None,
        error_code=error_code,
        decision=decision,
        gate=gate,
    )


# ---------------------------------------------------------------------------
# 6. Descriptor validation
# ---------------------------------------------------------------------------


def validate_handler_descriptor(
    descriptor: dict[str, Any],
    *,
    expected_canonical_name: str | None = None,
) -> str | None:
    """Validate a handler descriptor for safety.

    Returns error_code if validation fails, None if valid.

    Checks:
      - All required fields present and non-None
      - canonicalName is a non-empty string
      - allowlisted is True
      - dispatchAllowed is False
      - executionAllowed is False
      - providerSchemaAllowed is False
      - sideEffectFreeLookup is True
      - canonicalName matches expected (if provided)
    """
    if not isinstance(descriptor, dict):
        return ERROR_HANDLER_LOOKUP_DESCRIPTOR_INVALID

    # Check required fields
    for key in sorted(_REQUIRED_DESCRIPTOR_FIELDS):
        if key not in descriptor or descriptor[key] is None:
            return ERROR_HANDLER_LOOKUP_DESCRIPTOR_INVALID

    # Validate canonicalName is non-empty string
    canonical_name = descriptor.get("canonicalName")
    if not isinstance(canonical_name, str) or not canonical_name.strip():
        return ERROR_HANDLER_LOOKUP_DESCRIPTOR_INVALID

    # Validate allowlisted is True
    if descriptor.get("allowlisted") is not True:
        return ERROR_HANDLER_LOOKUP_NOT_ALLOWLISTED

    # Validate side-effect flags are safe
    if descriptor.get("dispatchAllowed") is not False:
        return ERROR_HANDLER_LOOKUP_SIDE_EFFECT_RISK
    if descriptor.get("executionAllowed") is not False:
        return ERROR_HANDLER_LOOKUP_SIDE_EFFECT_RISK
    if descriptor.get("providerSchemaAllowed") is not False:
        return ERROR_HANDLER_LOOKUP_SIDE_EFFECT_RISK

    # Validate sideEffectFreeLookup is True
    if descriptor.get("sideEffectFreeLookup") is not True:
        return ERROR_HANDLER_LOOKUP_SIDE_EFFECT_RISK

    # Validate canonicalName matches expected (if provided)
    if expected_canonical_name is not None:
        if canonical_name != expected_canonical_name:
            return ERROR_HANDLER_LOOKUP_POLICY_MISMATCH

    # Validate riskTier is a non-empty string
    risk_tier = descriptor.get("riskTier")
    if not isinstance(risk_tier, str) or not risk_tier.strip():
        return ERROR_HANDLER_LOOKUP_DESCRIPTOR_INVALID

    return None


# ---------------------------------------------------------------------------
# 7. Safe handler metadata lookup
# ---------------------------------------------------------------------------


def lookup_handler_descriptor(
    canonical_name: str,
    *,
    allowlist: frozenset[str] | None = None,
) -> HandlerLookupResult:
    """Look up safe handler descriptor for a canonical tool name.

    This function resolves safe handler metadata only. It does NOT:
      - Import any handler module
      - Instantiate any handler
      - Call any callable
      - Access ~/.hermes
      - Read production state.db
      - Read provider keys
      - Store raw confirmationToken
      - Store full tokenHash
      - Store raw arguments
      - Store secrets

    Handler existence is NOT permission. STATIC_ALLOWLIST is the permission
    boundary.

    Args:
        canonical_name: The tool canonical name to look up.
        allowlist: The STATIC_ALLOWLIST to check against. If None, uses the
            built-in allowlist check.

    Returns:
        HandlerLookupResult with safe handler descriptor or fail-closed result.
    """
    # Gate 46: Handler lookup enabled
    # Handler lookup is now enabled in this phase.

    # Gate 47: Handler registry / metadata source available
    if not isinstance(_SAFE_HANDLER_DESCRIPTORS, dict):
        return _fail_closed(
            error_code=ERROR_HANDLER_LOOKUP_REGISTRY_UNAVAILABLE,
            decision=DECISION_BLOCKED_HANDLER_LOOKUP_REGISTRY_UNAVAILABLE,
            gate="handler_registry",
        )

    # Check allowlist permission boundary FIRST
    # Handler existence is NOT permission.
    from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

    effective_allowlist = allowlist if allowlist is not None else STATIC_ALLOWLIST
    if canonical_name not in effective_allowlist:
        return _fail_closed(
            error_code=ERROR_HANDLER_LOOKUP_NOT_ALLOWLISTED,
            decision=DECISION_BLOCKED_HANDLER_LOOKUP_NOT_ALLOWLISTED,
            handler_lookup_status=HANDLER_LOOKUP_STATUS_BLOCKED,
            gate="handler_allowlist",
        )

    # Gate 48: Handler descriptor lookup by canonicalName
    raw_descriptor = _SAFE_HANDLER_DESCRIPTORS.get(canonical_name)
    if raw_descriptor is None:
        return _fail_closed(
            error_code=ERROR_HANDLER_LOOKUP_NOT_FOUND,
            decision=DECISION_BLOCKED_HANDLER_LOOKUP_NOT_FOUND,
            handler_lookup_status=HANDLER_LOOKUP_STATUS_NOT_FOUND,
            gate="handler_descriptor_lookup",
        )

    # Build a safe copy of the descriptor (no mutable references)
    safe_descriptor: dict[str, Any] = dict(raw_descriptor)

    # Gate 49–53: Validate descriptor
    validation_error = validate_handler_descriptor(
        safe_descriptor,
        expected_canonical_name=canonical_name,
    )
    if validation_error is not None:
        # Map validation error to appropriate decision
        if validation_error == ERROR_HANDLER_LOOKUP_NOT_ALLOWLISTED:
            decision = DECISION_BLOCKED_HANDLER_LOOKUP_NOT_ALLOWLISTED
        elif validation_error == ERROR_HANDLER_LOOKUP_SIDE_EFFECT_RISK:
            decision = DECISION_BLOCKED_HANDLER_LOOKUP_SIDE_EFFECT_RISK
        elif validation_error == ERROR_HANDLER_LOOKUP_POLICY_MISMATCH:
            decision = DECISION_BLOCKED_HANDLER_LOOKUP_POLICY_MISMATCH
        else:
            decision = DECISION_BLOCKED_HANDLER_LOOKUP_DESCRIPTOR_INVALID
        return _fail_closed(
            error_code=validation_error,
            decision=decision,
            handler_lookup_status=HANDLER_LOOKUP_STATUS_BLOCKED,
            gate="handler_descriptor_validation",
        )

    # Gate 52: Generate handlerLookupId
    handler_lookup_id = _generate_handler_lookup_id()
    now = _handler_lookup_now()

    # Build safe summary
    safe_summary = safe_handler_lookup_summary(
        handler_lookup_id=handler_lookup_id,
        handler_lookup_status=HANDLER_LOOKUP_STATUS_FOUND,
        canonical_name=canonical_name,
    )

    # Gate 53: Handler lookup safe response fields available
    return HandlerLookupResult(
        found=True,
        handler_lookup_id=handler_lookup_id,
        handler_lookup_status=HANDLER_LOOKUP_STATUS_FOUND,
        handler_descriptor=safe_descriptor,
        error_code=None,
        decision=None,  # Lookup success — no blocking decision
        gate=None,
        created_at=now.isoformat(),
        safe_summary=safe_summary,
    )


# ---------------------------------------------------------------------------
# 8. Safe summary builder
# ---------------------------------------------------------------------------


def safe_handler_lookup_summary(
    *,
    handler_lookup_id: str | None,
    handler_lookup_status: str,
    canonical_name: str | None = None,
) -> dict[str, Any]:
    """Build a safe summary from handler lookup result.

    Never exposes raw token, full tokenHash, raw arguments, callable object,
    function repr, provider credentials, secrets, or authorization headers.
    """
    summary: dict[str, Any] = {
        "handlerLookupId": handler_lookup_id,
        "handlerLookupStatus": handler_lookup_status,
    }
    if canonical_name is not None:
        summary["canonicalName"] = canonical_name
    return summary


# ---------------------------------------------------------------------------
# 9. Build handler descriptor (for external callers who need a standalone build)
# ---------------------------------------------------------------------------


def build_handler_descriptor(
    canonical_name: str,
) -> dict[str, Any] | None:
    """Build a safe handler descriptor for the given canonical name.

    Returns None if no safe descriptor is available.
    Never exposes callable objects, function repr, or secrets.
    """
    raw = _SAFE_HANDLER_DESCRIPTORS.get(canonical_name)
    if raw is None:
        return None
    return dict(raw)
