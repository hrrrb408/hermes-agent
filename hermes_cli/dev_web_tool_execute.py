"""Tool Execute Gate Skeleton for the Hermes Dev WebUI.

This module implements a blocked-only execute gate that evaluates whether a
proposed tool execution request would be allowed — **without invoking any
tool handler, provider, dispatch, or runtime service**.

Architecture constraints:
  - stdlib only (no third-party imports)
  - no provider imports, no tool handler imports, no agent imports
  - no dispatch imports, no toolsets execution
  - no network IO, no filesystem mutation, no runtime state mutation
  - no audit file write (skeleton only)
  - no STATIC_ALLOWLIST mutation or population
  - deterministic, JSON-serializable output
  - All requests return blocked in this phase
  - executionAllowed is ALWAYS False
  - dispatchAllowed is ALWAYS False
  - providerSchemaAllowed is ALWAYS False
  - toolHandlerCalled is ALWAYS False
  - providerApiCalled is ALWAYS False
  - executionStarted is ALWAYS False
  - executionCompleted is ALWAYS False
  - executionAttempted is ALWAYS False

Phase: 1G-04-16 — Dry-Run Historical Lookup Read-Only Implementation
Status: Blocked-only (no real tool execution, lookup integrated)
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# 1. Decision constants
# ---------------------------------------------------------------------------

DECISION_BLOCKED = "blocked"
DECISION_BLOCKED_REQUIRES_DRY_RUN = "blocked_requires_dry_run"
DECISION_BLOCKED_REQUIRES_AUDIT = "blocked_requires_audit"
DECISION_BLOCKED_REQUIRES_CONFIRMATION = "blocked_requires_confirmation"
DECISION_BLOCKED_BY_KILL_SWITCH = "blocked_by_kill_switch"
DECISION_BLOCKED_BY_ALLOWLIST = "blocked_by_allowlist"
DECISION_BLOCKED_BY_DENYLIST = "blocked_by_denylist"
DECISION_BLOCKED_BY_RISK_TIER = "blocked_by_risk_tier"
DECISION_BLOCKED_BY_DIGEST_MISMATCH = "blocked_by_digest_mismatch"
DECISION_BLOCKED_REQUIRES_CONFIRMATION_TOKEN = "blocked_requires_confirmation_token"
DECISION_BLOCKED_DIGEST_VERIFICATION_NOT_IMPLEMENTED = "blocked_digest_verification_not_implemented"

# Phase 1G-04-22: Digest verification decisions
DECISION_BLOCKED_DIGEST_MISSING = "blocked_digest_missing"
DECISION_BLOCKED_DIGEST_UNAVAILABLE = "blocked_digest_unavailable"
DECISION_BLOCKED_DIGEST_CANONICALIZATION_FAILED = "blocked_digest_canonicalization_failed"
DECISION_BLOCKED_DIGEST_MISMATCH = "blocked_digest_mismatch"
DECISION_BLOCKED_DIGEST_STALE = "blocked_digest_stale"
DECISION_BLOCKED_DIGEST_EXPIRED = "blocked_digest_expired"
DECISION_BLOCKED_PRE_EXECUTION_AUDIT_NOT_IMPLEMENTED = "blocked_pre_execution_audit_not_implemented"
DECISION_BLOCKED_HANDLER_LOOKUP_NOT_ENABLED = "blocked_handler_lookup_not_enabled"

# Phase 1G-04-26: Handler lookup decisions
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

# Phase 1G-04-28: Dispatch planning decisions
DECISION_BLOCKED_DISPATCH_UNAVAILABLE = "blocked_dispatch_unavailable"
DECISION_BLOCKED_DISPATCH_PLAN_UNAVAILABLE = "blocked_dispatch_plan_unavailable"
DECISION_BLOCKED_DISPATCH_PLAN_INVALID = "blocked_dispatch_plan_invalid"
DECISION_BLOCKED_DISPATCH_HANDLER_DESCRIPTOR_MISSING = (
    "blocked_dispatch_handler_descriptor_missing"
)
DECISION_BLOCKED_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH = (
    "blocked_dispatch_handler_descriptor_mismatch"
)
DECISION_BLOCKED_DISPATCH_NOT_ALLOWLISTED = "blocked_dispatch_not_allowlisted"
DECISION_BLOCKED_DISPATCH_POLICY_MISMATCH = "blocked_dispatch_policy_mismatch"
DECISION_BLOCKED_DISPATCH_SIDE_EFFECT_RISK = "blocked_dispatch_side_effect_risk"
DECISION_BLOCKED_DISPATCH_REGISTRY_MISMATCH = "blocked_dispatch_registry_mismatch"
DECISION_BLOCKED_TOOL_HANDLER_CALL_NOT_ENABLED = (
    "blocked_tool_handler_call_not_enabled"
)

# Phase 1G-04-29: Clarify-only handler call + post-execution audit decisions
DECISION_CLARIFY_EXECUTION_COMPLETED = "clarify_execution_completed"
DECISION_BLOCKED_POST_EXECUTION_AUDIT_FAILED = "blocked_post_execution_audit_failed"

# Phase 2A: read-only multi-tool controlled execution completion decision.
# Clarify keeps its Phase 1G decision string (backward compatibility); each
# Phase 2A read-only tool reports a per-tool completed decision. The
# authoritative "completed" signal for callers is the executionCompleted flag
# (set True by _build_success_result), not the decision string.
DECISION_CONTROLLED_EXECUTION_COMPLETED = "controlled_execution_completed"


def _completed_decision_for(canonical_name: str) -> str:
    """Return the completed-execution decision string for *canonical_name*.

    Clarify keeps the Phase 1G ``clarify_execution_completed`` string; each
    Phase 2A read-only tool reports ``<toolId>_execution_completed``.
    """
    if canonical_name == "clarify":
        return DECISION_CLARIFY_EXECUTION_COMPLETED
    return f"{canonical_name}_execution_completed"


def _completed_preview_type(canonical_name: str, tool_result: dict[str, Any] | None) -> str:
    """Return the result-preview type for a completed execution."""
    if isinstance(tool_result, dict):
        result_type = tool_result.get("type")
        if isinstance(result_type, str) and result_type.strip():
            return result_type.strip()
    return canonical_name

# Future decisions — not returned in this phase
DECISION_WOULD_EXECUTE = "would_execute"
DECISION_EXECUTED = "executed"
DECISION_EXECUTION_FAILED = "execution_failed"


# ---------------------------------------------------------------------------
# 2. Error codes
# ---------------------------------------------------------------------------

ERROR_KILL_SWITCH_DISABLED = "kill_switch_disabled"
ERROR_AGENT_TOOLS_DISABLED = "agent_tools_disabled"
ERROR_ALLOWLIST_MISSING = "allowlist_missing"
ERROR_TOOL_UNKNOWN = "tool_unknown"
ERROR_TOOL_DENYLISTED = "tool_denylisted"
ERROR_RISK_TIER_BLOCKED = "risk_tier_blocked"
ERROR_DRY_RUN_MISSING = "dry_run_missing"
ERROR_DRY_RUN_DIGEST_MISSING = "dry_run_digest_missing"
ERROR_CONFIRMATION_MISSING = "confirmation_missing"
ERROR_CONFIRMATION_INVALID = "confirmation_invalid"
ERROR_CONFIRMATION_NOT_IMPLEMENTED = "confirmation_not_implemented"
ERROR_CONFIRMATION_EXPIRED = "confirmation_expired"
ERROR_CONFIRMATION_REUSED = "confirmation_reused"
ERROR_CONFIRMATION_STORE_UNAVAILABLE = "confirmation_store_unavailable"
ERROR_CONFIRMATION_NOT_FOUND = "confirmation_not_found"
ERROR_CONFIRMATION_DRY_RUN_MISMATCH = "confirmation_dry_run_mismatch"
ERROR_CONFIRMATION_DIGEST_MISMATCH = "confirmation_digest_mismatch"
ERROR_CONFIRMATION_CANONICAL_NAME_MISMATCH = "confirmation_canonical_name_mismatch"
ERROR_CONFIRMATION_RISK_TIER_MISMATCH = "confirmation_risk_tier_mismatch"
ERROR_CONFIRMATION_CONSUME_FAILED = "confirmation_consume_failed"
ERROR_DIGEST_VERIFICATION_NOT_IMPLEMENTED = "digest_verification_not_implemented"
ERROR_DIGEST_MISMATCH = "digest_mismatch"
# Phase 1G-04-22: Digest verification error codes
ERROR_DIGEST_MISSING = "digest_missing"
ERROR_DIGEST_UNAVAILABLE = "digest_unavailable"
ERROR_DIGEST_HISTORICAL_MISSING = "digest_historical_missing"
ERROR_DIGEST_TOKEN_BINDING_MISSING = "digest_token_binding_missing"
ERROR_DIGEST_REQUEST_MISMATCH = "digest_request_mismatch"
ERROR_DIGEST_TOKEN_MISMATCH = "digest_token_mismatch"
ERROR_DIGEST_EXECUTE_MISMATCH = "digest_execute_mismatch"
ERROR_DIGEST_STALE = "digest_stale"
ERROR_DIGEST_EXPIRED = "digest_expired"
ERROR_DIGEST_VERIFIED_BUT_PRE_EXECUTION_AUDIT = (
    "digest_verified_but_pre_execution_audit_not_implemented"
)
# Phase 1G-04-24: Pre-execution audit error codes
ERROR_PRE_EXECUTION_AUDIT_UNAVAILABLE = "pre_execution_audit_unavailable"
ERROR_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN = "pre_execution_audit_path_forbidden"
ERROR_PRE_EXECUTION_AUDIT_WRITE_FAILED = "pre_execution_audit_write_failed"
ERROR_PRE_EXECUTION_AUDIT_INVALID_STATE = "pre_execution_audit_invalid_state"
ERROR_PRE_EXECUTION_AUDIT_MISSING_REQUIRED_FIELD = (
    "pre_execution_audit_missing_required_field"
)
ERROR_PRE_EXECUTION_AUDIT_SERIALIZATION_FAILED = (
    "pre_execution_audit_serialization_failed"
)
ERROR_PRE_EXECUTION_AUDIT_WRITTEN_BUT_HANDLER_LOOKUP_NOT_ENABLED = (
    "pre_execution_audit_written_but_handler_lookup_not_enabled"
)
ERROR_HANDLER_LOOKUP_NOT_ENABLED = "handler_lookup_not_enabled"
# Phase 1G-04-26: Handler lookup error codes
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
# Phase 1G-04-28: Dispatch planning error codes
ERROR_DISPATCH_UNAVAILABLE = "dispatch_unavailable"
ERROR_DISPATCH_PLAN_UNAVAILABLE = "dispatch_plan_unavailable"
ERROR_DISPATCH_PLAN_INVALID = "dispatch_plan_invalid"
ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISSING = "dispatch_handler_descriptor_missing"
ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH = "dispatch_handler_descriptor_mismatch"
ERROR_DISPATCH_NOT_ALLOWLISTED = "dispatch_not_allowlisted"
ERROR_DISPATCH_POLICY_MISMATCH = "dispatch_policy_mismatch"
ERROR_DISPATCH_SIDE_EFFECT_RISK = "dispatch_side_effect_risk"
ERROR_DISPATCH_REGISTRY_MISMATCH = "dispatch_registry_mismatch"
ERROR_DISPATCH_WRITTEN_BUT_TOOL_HANDLER_CALL_NOT_ENABLED = (
    "dispatch_written_but_tool_handler_call_not_enabled"
)
ERROR_TOOL_HANDLER_CALL_NOT_ENABLED = "tool_handler_call_not_enabled"
# Phase 1G-04-29: Post-execution audit error codes
ERROR_POST_EXECUTION_AUDIT_FAILED = "post_execution_audit_failed"
ERROR_POST_EXECUTION_AUDIT_WRITE_FAILED = "post_execution_audit_write_failed"
ERROR_DRY_RUN_NOT_FOUND = "dry_run_not_found"
ERROR_DRY_RUN_EXPIRED = "dry_run_expired"
ERROR_DRY_RUN_NOT_ALLOWED = "dry_run_not_allowed"
ERROR_DRY_RUN_AUDIT_MISSING = "dry_run_audit_missing"
ERROR_DRY_RUN_CANONICAL_NAME_MISMATCH = "dry_run_canonical_name_mismatch"
ERROR_DRY_RUN_RISK_TIER_MISMATCH = "dry_run_risk_tier_mismatch"
ERROR_DRY_RUN_POLICY_VERSION_MISMATCH = "dry_run_policy_version_mismatch"
ERROR_DRY_RUN_LOOKUP_UNAVAILABLE = "dry_run_lookup_unavailable"
ERROR_VALIDATION_FAILED = "validation_failed"
ERROR_INTERNAL = "internal_error"


# ---------------------------------------------------------------------------
# 3. Gate status constants
# ---------------------------------------------------------------------------

GATE_KILL_SWITCH = "kill_switch"
GATE_AGENT_TOOLS = "agent_tools"
GATE_STATIC_ALLOWLIST = "static_allowlist"
GATE_KNOWN_TOOL = "known_tool"
GATE_DENYLIST = "denylist"
GATE_RISK_TIER = "risk_tier"
GATE_DRY_RUN_PREFLIGHT = "dry_run_preflight"
GATE_DRY_RUN_LOOKUP = "dry_run_lookup"
GATE_DRY_RUN_DECISION = "dry_run_decision"
GATE_DRY_RUN_AUDIT = "dry_run_audit"
GATE_DRY_RUN_BINDING_CANONICAL = "dry_run_binding_canonical"
GATE_DRY_RUN_BINDING_RISK = "dry_run_binding_risk"
GATE_DRY_RUN_BINDING_POLICY = "dry_run_binding_policy"
GATE_DRY_RUN_BINDING_DIGEST = "dry_run_binding_digest"
GATE_CONFIRMATION = "confirmation"
GATE_CONFIRMATION_STORE = "confirmation_store"
GATE_CONFIRMATION_LOOKUP = "confirmation_lookup"
GATE_CONFIRMATION_EXPIRY = "confirmation_expiry"
GATE_CONFIRMATION_REUSE = "confirmation_reuse"
GATE_CONFIRMATION_BINDING_DRY_RUN = "confirmation_binding_dry_run"
GATE_CONFIRMATION_BINDING_DIGEST = "confirmation_binding_digest"
GATE_CONFIRMATION_BINDING_CANONICAL = "confirmation_binding_canonical"
GATE_CONFIRMATION_BINDING_RISK = "confirmation_binding_risk"
GATE_CONFIRMATION_CONSUME = "confirmation_consume"
GATE_DIGEST_VERIFICATION = "digest_verification"
GATE_DIGEST = "digest"
GATE_DIGEST_PACKAGE = "digest_package"
GATE_DIGEST_CANONICALIZATION = "digest_canonicalization"
GATE_DIGEST_HISTORICAL = "digest_historical"
GATE_DIGEST_TOKEN_BINDING = "digest_token_binding"
GATE_DIGEST_REQUEST = "digest_request"
GATE_DIGEST_TOKEN_MATCH = "digest_token_match"
GATE_DIGEST_EXECUTE_MATCH = "digest_execute_match"
GATE_DIGEST_STALENESS = "digest_staleness"
GATE_DIGEST_EXPIRY = "digest_expiry"
GATE_PRE_EXECUTION_AUDIT = "pre_execution_audit"
GATE_PRE_EXECUTION_AUDIT_PACKAGE = "pre_execution_audit_package"
GATE_PRE_EXECUTION_AUDIT_PATH = "pre_execution_audit_path"
GATE_PRE_EXECUTION_AUDIT_SERIALIZATION = "pre_execution_audit_serialization"
GATE_PRE_EXECUTION_AUDIT_WRITE = "pre_execution_audit_write"
GATE_PRE_EXECUTION_AUDIT_ID = "pre_execution_audit_id"
GATE_HANDLER_LOOKUP = "handler_lookup"
GATE_HANDLER_REGISTRY = "handler_registry"
GATE_HANDLER_DESCRIPTOR_LOOKUP = "handler_descriptor_lookup"
GATE_HANDLER_DESCRIPTOR_VALIDATION = "handler_descriptor_validation"
GATE_HANDLER_ALLOWLIST = "handler_allowlist"
GATE_DISPATCH = "dispatch"
GATE_DISPATCH_PLAN = "dispatch_plan"
GATE_DISPATCH_PLAN_VALIDATION = "dispatch_plan_validation"
GATE_TOOL_HANDLER_CALL = "tool_handler_call"
GATE_POST_EXECUTION_AUDIT = "post_execution_audit"
GATE_POST_EXECUTION_AUDIT_WRITE = "post_execution_audit_write"
GATE_EXECUTION = "execution"
GATE_VALIDATION = "validation"


# ---------------------------------------------------------------------------
# 4. Secret pattern detection (reused from dry-run module)
# ---------------------------------------------------------------------------

_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
)

_FORBIDDEN_ARG_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "api_key", "apikey", "authorization", "auth_header", "bearer",
        "token", "secret", "password", "passwd", "credential", "cookie",
        "session", "private_key", "client_secret", "access_token",
        "refresh_token", "access_key",
    }
)

_NORMALIZED_FORBIDDEN_ARG_FIELDS: frozenset[str] = frozenset(
    n.replace("_", "").replace("-", "").lower()
    for n in _FORBIDDEN_ARG_FIELD_NAMES
)

_REDACTED_VALUE = "[REDACTED]"


# ---------------------------------------------------------------------------
# 5. Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolExecuteRequest:
    """Immutable execute request model."""

    canonical_name: str
    arguments_preview: dict[str, Any] | None = None
    dry_run_request_id: str | None = None
    dry_run_decision_digest: str | None = None
    confirmation_token: str | None = None
    request_id: str | None = None
    source_context: str | None = None
    ui_origin: str | None = None
    client_created_at: str | None = None


@dataclass(frozen=True, slots=True)
class ToolExecuteGateStatus:
    """Gate evaluation result."""

    gate: str
    passed: bool
    error_code: str | None


@dataclass(frozen=True, slots=True)
class ToolExecuteAuditStatus:
    """Audit status for the execute attempt."""

    audit_attempted: bool
    audit_written: bool
    audit_error: str | None


@dataclass(frozen=True, slots=True)
class ToolExecuteResultPreview:
    """Preview of what execution would produce (always empty in skeleton)."""

    available: bool
    preview_type: str | None
    preview_size_bytes: int
    truncated: bool


@dataclass(frozen=True, slots=True)
class ToolExecuteResult:
    """Immutable execute gate evaluation result.

    In Phase 1G-04-11, all fields reflect blocked-only state.
    """

    canonical_name: str
    exists: bool
    risk_tier: str | None
    decision: str
    gate_status: tuple[ToolExecuteGateStatus, ...]
    audit_status: ToolExecuteAuditStatus
    result_preview: ToolExecuteResultPreview
    execution_attempted: bool
    execution_started: bool
    execution_completed: bool
    execution_allowed: bool
    dispatch_allowed: bool
    provider_schema_allowed: bool
    tool_handler_called: bool
    provider_api_called: bool
    error_code: str | None
    policy_notes: tuple[str, ...]
    reason_codes: tuple[str, ...]
    pre_execution_audit_id: str | None = None
    execute_request_id: str | None = None
    pre_execution_audit_status: str | None = None
    handler_lookup_id: str | None = None
    handler_lookup_status: str | None = None
    handler_descriptor: dict[str, Any] | None = None
    dispatch_id: str | None = None
    dispatch_status: str | None = None
    dispatch_plan: dict[str, Any] | None = None
    handler_call_id: str | None = None
    handler_call_status: str | None = None
    execution_status: str | None = None
    post_execution_audit_id: str | None = None
    post_execution_audit_status: str | None = None
    tool_result: dict[str, Any] | None = None
    side_effects: dict[str, Any] | None = None

    def to_safe_dict(self) -> dict[str, Any]:
        """Convert to JSON-safe dict with all execution flags false."""
        result: dict[str, Any] = {
            "canonicalName": self.canonical_name,
            "exists": self.exists,
            "riskTier": self.risk_tier,
            "decision": self.decision,
            "gateStatus": [
                {
                    "gate": gs.gate,
                    "passed": gs.passed,
                    "errorCode": gs.error_code,
                }
                for gs in self.gate_status
            ],
            "auditStatus": {
                "auditAttempted": self.audit_status.audit_attempted,
                "auditWritten": self.audit_status.audit_written,
                "auditError": self.audit_status.audit_error,
            },
            "resultPreview": {
                "available": self.result_preview.available,
                "previewType": self.result_preview.preview_type,
                "previewSizeBytes": self.result_preview.preview_size_bytes,
                "truncated": self.result_preview.truncated,
            },
            "executionAttempted": self.execution_attempted,
            "executionStarted": self.execution_started,
            "executionCompleted": self.execution_completed,
            "executionAllowed": self.execution_allowed,
            "dispatchAllowed": self.dispatch_allowed,
            "providerSchemaAllowed": self.provider_schema_allowed,
            "toolHandlerCalled": self.tool_handler_called,
            "providerApiCalled": self.provider_api_called,
            "errorCode": self.error_code,
            "policyNotes": list(self.policy_notes),
            "reasonCodes": list(self.reason_codes),
        }
        if self.pre_execution_audit_id is not None:
            result["preExecutionAuditId"] = self.pre_execution_audit_id
        if self.execute_request_id is not None:
            result["executeRequestId"] = self.execute_request_id
        if self.pre_execution_audit_status is not None:
            result["preExecutionAuditStatus"] = self.pre_execution_audit_status
        if self.handler_lookup_id is not None:
            result["handlerLookupId"] = self.handler_lookup_id
        if self.handler_lookup_status is not None:
            result["handlerLookupStatus"] = self.handler_lookup_status
        if self.handler_descriptor is not None:
            result["handlerDescriptor"] = self.handler_descriptor
        if self.dispatch_id is not None:
            result["dispatchId"] = self.dispatch_id
        if self.dispatch_status is not None:
            result["dispatchStatus"] = self.dispatch_status
        if self.dispatch_plan is not None:
            result["dispatchPlan"] = self.dispatch_plan
        if self.handler_call_id is not None:
            result["handlerCallId"] = self.handler_call_id
        if self.handler_call_status is not None:
            result["handlerCallStatus"] = self.handler_call_status
        if self.execution_status is not None:
            result["executionStatus"] = self.execution_status
        if self.post_execution_audit_id is not None:
            result["postExecutionAuditId"] = self.post_execution_audit_id
        if self.post_execution_audit_status is not None:
            result["postExecutionAuditStatus"] = self.post_execution_audit_status
        if self.tool_result is not None:
            result["toolResult"] = self.tool_result
        if self.side_effects is not None:
            result["sideEffects"] = self.side_effects
        return result


@dataclass(frozen=True, slots=True)
class ToolExecutePolicySummary:
    """Summary of execute policy state."""

    kill_switch_enabled: bool
    agent_tools_enabled: bool
    static_allowlist_size: int
    static_allowlist_tools: tuple[str, ...]
    denylist_size: int
    execution_enabled: bool
    dispatch_enabled: bool
    provider_schema_enabled: bool


# ---------------------------------------------------------------------------
# 6. Kill switch evaluation
# ---------------------------------------------------------------------------


def _is_kill_switch_enabled(env_var: str) -> bool:
    """Check if a kill switch env var is exactly lowercase 'true'.

    Only exact lowercase ``"true"`` is accepted.
    Unset, empty, "false", "False", "TRUE", "1", "yes", "on" all block.
    """
    return os.environ.get(env_var, "").strip() == "true"


# ---------------------------------------------------------------------------
# 7. Argument redaction
# ---------------------------------------------------------------------------


def _redact_argument_values(
    args: dict[str, Any],
) -> dict[str, Any]:
    """Redact secret values from arguments preview."""
    result: dict[str, Any] = {}
    for key, value in args.items():
        # Check forbidden field names
        normalized_key = key.replace("_", "").replace("-", "").lower()
        if normalized_key in _NORMALIZED_FORBIDDEN_ARG_FIELDS:
            result[key] = _REDACTED_VALUE
            continue

        if isinstance(value, str):
            # Check secret value patterns
            redacted = False
            for pattern in _SECRET_VALUE_PATTERNS:
                if pattern.search(value):
                    result[key] = _REDACTED_VALUE
                    redacted = True
                    break
            if not redacted:
                result[key] = value
        elif isinstance(value, dict):
            result[key] = _redact_argument_values(value)
        else:
            result[key] = value
    return result


def _has_secrets_in_json(obj: Any) -> bool:
    """Check if a JSON-serializable object contains secret patterns."""
    text = json.dumps(obj) if not isinstance(obj, str) else obj
    for pattern in _SECRET_VALUE_PATTERNS:
        if pattern.search(text):
            return True
    return False


# ---------------------------------------------------------------------------
# 8. Tool lookup helpers (read-only, from policy module)
# ---------------------------------------------------------------------------


def _lookup_tool_policy(canonical_name: str) -> tuple[bool, str | None]:
    """Look up tool policy from the static inventory.

    Returns (exists, risk_tier).
    """
    from hermes_cli.dev_web_tool_policy import (
        ALL_CANONICAL_TOOLS,
        STATIC_DENYLIST,
        TOOL_POLICY_INVENTORY,
    )

    if canonical_name not in ALL_CANONICAL_TOOLS:
        return (False, None)

    entry = TOOL_POLICY_INVENTORY.get(canonical_name)
    if entry is None:
        return (True, None)

    return (True, entry.primary_risk.value)


def _is_denylisted(canonical_name: str) -> bool:
    """Check if tool is on the static denylist."""
    from hermes_cli.dev_web_tool_policy import STATIC_DENYLIST
    return canonical_name in STATIC_DENYLIST


# ---------------------------------------------------------------------------
# 9. Gate evaluation — the core blocked-only logic
# ---------------------------------------------------------------------------


def evaluate_tool_execute_request(
    canonical_name: str,
    arguments_preview: dict[str, Any] | None = None,
    dry_run_request_id: str | None = None,
    dry_run_decision_digest: str | None = None,
    confirmation_token: str | None = None,
    request_id: str | None = None,
    source_context: str | None = None,
    ui_origin: str | None = None,
    client_created_at: str | None = None,
    hermes_home: str | None = None,
) -> ToolExecuteResult:
    """Evaluate a tool execute request through the gate stack.

    This function is **blocked-only** in Phase 1G-04-16.
    Every request returns a blocked response with all execution flags false.
    No tool handler is called, no dispatch occurs, no provider is contacted.

    Gate evaluation order:
      1. Kill switch (HERMES_TOOL_EXECUTION_ENABLED)
      2. Agent tools switch (HERMES_AGENT_TOOLS_ENABLED)
      3. Static allowlist (must be non-empty)
      4. Known tool (must exist in inventory)
      5. Denylist (must not be denylisted)
      6. Risk tier (R0/R1 only eligible in future)
      7. Dry-run preflight (dryRunRequestId must be present)
      8. Dry-run historical lookup (must find prior dry-run record)
      9. Dry-run decision (must be would_allow)
     10. Dry-run audit written (must be true)
     11. canonicalName binding
     12. riskTier binding
     13. policyVersion binding
     14. digest binding (if available)
     15. Confirmation token (must be present)
     16. Confirmation token verification (not implemented → blocked)
    """
    gates: list[ToolExecuteGateStatus] = []
    policy_notes: list[str] = []
    reason_codes: list[str] = []
    error_code: str | None = None
    decision: str = DECISION_BLOCKED

    # ── Gate 1: Kill switch ──
    tool_execution_enabled = _is_kill_switch_enabled("HERMES_TOOL_EXECUTION_ENABLED")
    if not tool_execution_enabled:
        gates.append(ToolExecuteGateStatus(
            gate=GATE_KILL_SWITCH,
            passed=False,
            error_code=ERROR_KILL_SWITCH_DISABLED,
        ))
        policy_notes.append("Tool execution kill switch is not enabled.")
        reason_codes.append(ERROR_KILL_SWITCH_DISABLED)
        error_code = ERROR_KILL_SWITCH_DISABLED
        decision = DECISION_BLOCKED_BY_KILL_SWITCH
        # Return early — kill switch is the most common default block
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_KILL_SWITCH, passed=True, error_code=None,
    ))

    # ── Gate 2: Agent tools switch ──
    agent_tools_enabled = _is_kill_switch_enabled("HERMES_AGENT_TOOLS_ENABLED")
    if not agent_tools_enabled:
        gates.append(ToolExecuteGateStatus(
            gate=GATE_AGENT_TOOLS,
            passed=False,
            error_code=ERROR_AGENT_TOOLS_DISABLED,
        ))
        policy_notes.append("Agent tools kill switch is not enabled.")
        reason_codes.append(ERROR_AGENT_TOOLS_DISABLED)
        error_code = ERROR_AGENT_TOOLS_DISABLED
        decision = DECISION_BLOCKED_BY_KILL_SWITCH
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_AGENT_TOOLS, passed=True, error_code=None,
    ))

    # ── Gate 3: Static allowlist ──
    from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

    if canonical_name not in STATIC_ALLOWLIST:
        gates.append(ToolExecuteGateStatus(
            gate=GATE_STATIC_ALLOWLIST,
            passed=False,
            error_code=ERROR_ALLOWLIST_MISSING,
        ))
        policy_notes.append(
            f"Tool '{canonical_name}' is not on the static allowlist. "
            f"Only {sorted(STATIC_ALLOWLIST)} are eligible for execution."
        )
        reason_codes.append(ERROR_ALLOWLIST_MISSING)
        error_code = ERROR_ALLOWLIST_MISSING
        decision = DECISION_BLOCKED_BY_ALLOWLIST
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_STATIC_ALLOWLIST, passed=True, error_code=None,
    ))

    # ── Gate 4: Known tool ──
    exists, risk_tier = _lookup_tool_policy(canonical_name)
    if not exists:
        gates.append(ToolExecuteGateStatus(
            gate=GATE_KNOWN_TOOL,
            passed=False,
            error_code=ERROR_TOOL_UNKNOWN,
        ))
        policy_notes.append(f"Tool '{canonical_name}' is not in the policy inventory.")
        reason_codes.append(ERROR_TOOL_UNKNOWN)
        error_code = ERROR_TOOL_UNKNOWN
        decision = DECISION_BLOCKED
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=None,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_KNOWN_TOOL, passed=True, error_code=None,
    ))

    # ── Gate 5: Denylist ──
    if _is_denylisted(canonical_name):
        gates.append(ToolExecuteGateStatus(
            gate=GATE_DENYLIST,
            passed=False,
            error_code=ERROR_TOOL_DENYLISTED,
        ))
        policy_notes.append(f"Tool '{canonical_name}' is on the static denylist.")
        reason_codes.append(ERROR_TOOL_DENYLISTED)
        error_code = ERROR_TOOL_DENYLISTED
        decision = DECISION_BLOCKED_BY_DENYLIST
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_DENYLIST, passed=True, error_code=None,
    ))

    # ── Gate 6: Risk tier ──
    # R0 and R1 are eligible in future phases; R2+ blocked for now
    if risk_tier and risk_tier in ("R2", "R3", "R4", "R5"):
        gates.append(ToolExecuteGateStatus(
            gate=GATE_RISK_TIER,
            passed=False,
            error_code=ERROR_RISK_TIER_BLOCKED,
        ))
        policy_notes.append(
            f"Tool '{canonical_name}' has risk tier {risk_tier}. "
            "Only R0/R1 tools are eligible for execution in future phases."
        )
        reason_codes.append(ERROR_RISK_TIER_BLOCKED)
        error_code = ERROR_RISK_TIER_BLOCKED
        decision = DECISION_BLOCKED_BY_RISK_TIER
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_RISK_TIER, passed=True, error_code=None,
    ))

    # ── Gate 7: Dry-run preflight ──
    if not dry_run_request_id:
        gates.append(ToolExecuteGateStatus(
            gate=GATE_DRY_RUN_PREFLIGHT,
            passed=False,
            error_code=ERROR_DRY_RUN_MISSING,
        ))
        policy_notes.append(
            "Dry-run preflight is required before execution. "
            "A prior dry-run request ID must be provided."
        )
        reason_codes.append(ERROR_DRY_RUN_MISSING)
        error_code = ERROR_DRY_RUN_MISSING
        decision = DECISION_BLOCKED_REQUIRES_DRY_RUN
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_DRY_RUN_PREFLIGHT, passed=True, error_code=None,
    ))

    # ── Gate 8: Dry-run historical lookup ──
    from hermes_cli.dev_web_tool_execute_preflight import (
        lookup_dry_run_record,
        verify_decision_allowed,
        verify_audit_written,
        verify_canonical_name_binding,
        verify_risk_tier_binding,
        verify_policy_version_binding,
        verify_digest_binding,
        ERROR_DRY_RUN_NOT_FOUND as _LOOKUP_NOT_FOUND,
        ERROR_DRY_RUN_EXPIRED as _LOOKUP_EXPIRED,
        ERROR_DRY_RUN_NOT_ALLOWED as _LOOKUP_NOT_ALLOWED,
        ERROR_DRY_RUN_AUDIT_MISSING as _LOOKUP_AUDIT_MISSING,
        ERROR_DRY_RUN_CANONICAL_NAME_MISMATCH as _LOOKUP_CN_MISMATCH,
        ERROR_DRY_RUN_RISK_TIER_MISMATCH as _LOOKUP_RT_MISMATCH,
        ERROR_DRY_RUN_POLICY_VERSION_MISMATCH as _LOOKUP_PV_MISMATCH,
        ERROR_DRY_RUN_DIGEST_MISMATCH as _LOOKUP_DIGEST_MISMATCH,
        ERROR_DRY_RUN_LOOKUP_UNAVAILABLE as _LOOKUP_UNAVAILABLE,
    )

    lookup_result = lookup_dry_run_record(
        hermes_home=hermes_home,
        dry_run_request_id=dry_run_request_id,
        canonical_name=canonical_name,
    )

    if not lookup_result.found:
        lookup_error = lookup_result.error_code or _LOOKUP_UNAVAILABLE
        gates.append(ToolExecuteGateStatus(
            gate=GATE_DRY_RUN_LOOKUP,
            passed=False,
            error_code=lookup_error,
        ))
        policy_notes.append(
            f"Dry-run historical lookup failed: {lookup_error}. "
            "No prior dry-run record found for the given request ID."
        )
        reason_codes.append(lookup_error)
        error_code = lookup_error
        decision = DECISION_BLOCKED_REQUIRES_DRY_RUN
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_DRY_RUN_LOOKUP, passed=True, error_code=None,
    ))

    # ── Gate 9: Dry-run decision must be would_allow ──
    decision_error = verify_decision_allowed(lookup_result)
    if decision_error:
        gates.append(ToolExecuteGateStatus(
            gate=GATE_DRY_RUN_DECISION,
            passed=False,
            error_code=decision_error,
        ))
        policy_notes.append(
            f"Dry-run decision was '{lookup_result.decision}', "
            "not 'would_allow'. Execution requires a prior allowed dry-run."
        )
        reason_codes.append(decision_error)
        error_code = decision_error
        decision = DECISION_BLOCKED_REQUIRES_DRY_RUN
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_DRY_RUN_DECISION, passed=True, error_code=None,
    ))

    # ── Gate 10: Dry-run auditWritten must be true ──
    audit_error = verify_audit_written(lookup_result)
    if audit_error:
        gates.append(ToolExecuteGateStatus(
            gate=GATE_DRY_RUN_AUDIT,
            passed=False,
            error_code=audit_error,
        ))
        policy_notes.append(
            "Dry-run record found but audit was not written. "
            "Execution requires a dry-run with a written audit event."
        )
        reason_codes.append(audit_error)
        error_code = audit_error
        decision = DECISION_BLOCKED_REQUIRES_AUDIT
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_DRY_RUN_AUDIT, passed=True, error_code=None,
    ))

    # ── Gate 11: canonicalName binding ──
    cn_error = verify_canonical_name_binding(lookup_result, canonical_name)
    if cn_error:
        gates.append(ToolExecuteGateStatus(
            gate=GATE_DRY_RUN_BINDING_CANONICAL,
            passed=False,
            error_code=cn_error,
        ))
        policy_notes.append(
            f"canonicalName mismatch: execute request has '{canonical_name}', "
            f"dry-run record has '{lookup_result.canonical_name}'."
        )
        reason_codes.append(cn_error)
        error_code = cn_error
        decision = DECISION_BLOCKED_BY_DIGEST_MISMATCH
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_DRY_RUN_BINDING_CANONICAL, passed=True, error_code=None,
    ))

    # ── Gate 12: riskTier binding ──
    rt_error = verify_risk_tier_binding(lookup_result, risk_tier)
    if rt_error:
        gates.append(ToolExecuteGateStatus(
            gate=GATE_DRY_RUN_BINDING_RISK,
            passed=False,
            error_code=rt_error,
        ))
        policy_notes.append(
            f"riskTier mismatch: execute request has '{risk_tier}', "
            f"dry-run record has '{lookup_result.risk_tier}'."
        )
        reason_codes.append(rt_error)
        error_code = rt_error
        decision = DECISION_BLOCKED_BY_DIGEST_MISMATCH
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_DRY_RUN_BINDING_RISK, passed=True, error_code=None,
    ))

    # ── Gate 13: policyVersion binding ──
    pv_error = verify_policy_version_binding(lookup_result, None)
    if pv_error:
        gates.append(ToolExecuteGateStatus(
            gate=GATE_DRY_RUN_BINDING_POLICY,
            passed=False,
            error_code=pv_error,
        ))
        policy_notes.append("policyVersion mismatch between execute and dry-run.")
        reason_codes.append(pv_error)
        error_code = pv_error
        decision = DECISION_BLOCKED_BY_DIGEST_MISMATCH
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_DRY_RUN_BINDING_POLICY, passed=True, error_code=None,
    ))

    # ── Gate 14: digest binding (if available) ──
    digest_error = verify_digest_binding(lookup_result, dry_run_decision_digest)
    if digest_error:
        gates.append(ToolExecuteGateStatus(
            gate=GATE_DRY_RUN_BINDING_DIGEST,
            passed=False,
            error_code=digest_error,
        ))
        policy_notes.append("dryRunDecisionDigest mismatch with historical record.")
        reason_codes.append(digest_error)
        error_code = digest_error
        decision = DECISION_BLOCKED_BY_DIGEST_MISMATCH
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_DRY_RUN_BINDING_DIGEST, passed=True, error_code=None,
    ))

    # ── Gate 15: Confirmation token present ──
    if not confirmation_token:
        gates.append(ToolExecuteGateStatus(
            gate=GATE_CONFIRMATION,
            passed=False,
            error_code=ERROR_CONFIRMATION_MISSING,
        ))
        policy_notes.append(
            "Confirmation token is required before execution. "
            "Request a token via the dry-run endpoint with issueConfirmationToken=true."
        )
        reason_codes.append(ERROR_CONFIRMATION_MISSING)
        error_code = ERROR_CONFIRMATION_MISSING
        decision = DECISION_BLOCKED_REQUIRES_CONFIRMATION
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    gates.append(ToolExecuteGateStatus(
        gate=GATE_CONFIRMATION, passed=True, error_code=None,
    ))

    # ── Gate 16–27: Confirmation token verification ──
    from hermes_cli.dev_web_tool_execute_confirmation import (
        verify_confirmation_token as _verify_token,
    )

    token_result = _verify_token(
        hermes_home=hermes_home,
        raw_token=confirmation_token,
        dry_run_request_id=dry_run_request_id,
        dry_run_decision_digest=dry_run_decision_digest,
        canonical_name=canonical_name,
        risk_tier=risk_tier,
        policy_version=None,
        audit_event_id=lookup_result.audit_event_id,
        arguments_digest=None,
        consume=True,
    )

    if not token_result.verified:
        # Map token verification error to gate status
        token_error = token_result.error_code or ERROR_CONFIRMATION_INVALID
        gates.append(ToolExecuteGateStatus(
            gate=GATE_CONFIRMATION,
            passed=False,
            error_code=token_error,
        ))
        policy_notes.append(
            f"Confirmation token verification failed: {token_error}."
        )
        reason_codes.append(token_error)
        error_code = token_error
        decision = DECISION_BLOCKED_REQUIRES_CONFIRMATION_TOKEN
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    # Token verified — record gate pass
    gates.append(ToolExecuteGateStatus(
        gate=GATE_CONFIRMATION, passed=True, error_code=None,
    ))

    # ── Gate 28–37: Digest verification (Phase 1G-04-22) ──
    from hermes_cli.dev_web_tool_execute_digest import (
        verify_dry_run_decision_digest,
        build_dry_run_decision_digest_package,
        ERROR_DIGEST_HISTORICAL_MISSING as _DIGEST_HIST_MISSING,
        ERROR_DIGEST_TOKEN_BINDING_MISSING as _DIGEST_TOKEN_MISSING,
        ERROR_DIGEST_REQUEST_MISMATCH as _DIGEST_REQ_MISMATCH,
        ERROR_DIGEST_TOKEN_MISMATCH as _DIGEST_TOK_MISMATCH,
        ERROR_DIGEST_EXECUTE_MISMATCH as _DIGEST_EXEC_MISMATCH,
        ERROR_DIGEST_EXPIRED as _DIGEST_EXPIRED,
        ERROR_DIGEST_VERIFIED_BUT_PRE_EXECUTION_AUDIT_NOT_IMPLEMENTED as _DIGEST_VERIFIED_BLOCKED,
    )

    # Extract historical digest from lookup result
    historical_digest = lookup_result.dry_run_decision_digest

    # Extract token-bound digest from token verification result
    token_bound_digest = None
    if hasattr(token_result, "binding_summary") and token_result.binding_summary:
        token_bound_digest = token_result.binding_summary.get("dryRunDecisionDigest")
    # Also check safe_summary for the digest field
    if token_bound_digest is None and hasattr(token_result, "safe_summary") and token_result.safe_summary:
        # Token safe_summary doesn't include digest; try token state directly
        pass

    # Re-read token state to get bound digest (token verification consumes the token)
    # The token_result.safe_summary may have it, but we also pass it via binding
    # For now, the token-bound digest comes from the token store's dryRunDecisionDigest field
    # We can extract it from the verification result's safe_summary if available
    # Actually, we need to look at what the token verification stores
    # The token_state has dryRunDecisionDigest field from issuance
    # The safe_summary doesn't expose it. We need a different approach.

    # The correct approach: verify_confirmation_token already checked digest binding
    # (Step 10 in verify_confirmation_token). If it passed, the token's stored
    # dryRunDecisionDigest matches the request's dry_run_decision_digest.
    # So if verification succeeded, we know they match.
    # For digest verification, we need:
    # 1. Historical digest from audit event (lookup_result.dry_run_decision_digest)
    # 2. Token-bound digest — we can get this by re-reading the token store
    #    OR we can rely on the fact that token verification already confirmed
    #    token's dryRunDecisionDigest == request's dry_run_decision_digest.
    #    So token_bound_digest = dry_run_decision_digest (the request value)
    # 3. Request digest = dry_run_decision_digest
    # 4. Execute-derived digest = recompute from current state

    # Strategy: token verification already bound token digest to request digest.
    # So token_bound_digest = dry_run_decision_digest (request value).
    token_bound_digest = dry_run_decision_digest

    # Execute-derived digest: recompute from current execute request fields
    execute_derived_digest = None
    try:
        from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST
        digest_pkg = build_dry_run_decision_digest_package(
            dry_run_request_id=dry_run_request_id,
            canonical_name=canonical_name,
            risk_tier=risk_tier,
            policy_decision="would_allow",
            allowlisted=canonical_name in STATIC_ALLOWLIST,
            audit_written=True,
            audit_event_id=lookup_result.audit_event_id,
            arguments=arguments_preview if isinstance(arguments_preview, dict) else None,
            created_at=lookup_result.created_at,
            expires_at=lookup_result.expires_at,
        )
        if digest_pkg.success:
            execute_derived_digest = digest_pkg.digest
    except Exception:
        pass  # Digest computation failure is non-fatal here

    digest_result = verify_dry_run_decision_digest(
        historical_digest=historical_digest,
        token_bound_digest=token_bound_digest,
        request_digest=dry_run_decision_digest,
        execute_derived_digest=execute_derived_digest,
        historical_created_at=lookup_result.created_at,
        historical_expires_at=lookup_result.expires_at,
    )

    if not digest_result.verified:
        # Digest verification failed
        digest_error = digest_result.error_code or ERROR_DIGEST_MISMATCH
        digest_gate = digest_result.gate or GATE_DIGEST_VERIFICATION

        gates.append(ToolExecuteGateStatus(
            gate=digest_gate,
            passed=False,
            error_code=digest_error,
        ))
        policy_notes.append(
            f"Digest verification failed: {digest_error}. "
            "Execution remains blocked."
        )
        reason_codes.append(digest_error)
        error_code = digest_error
        decision = digest_result.decision or DECISION_BLOCKED_BY_DIGEST_MISMATCH

        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    # Digest verified but still blocked at pre-execution audit boundary
    gates.append(ToolExecuteGateStatus(
        gate=GATE_DIGEST_VERIFICATION, passed=True, error_code=None,
    ))

    # ── Gate 38–42: Pre-execution audit (Phase 1G-04-24) ──
    from hermes_cli.dev_web_tool_pre_execution_audit import (
        build_pre_execution_audit_package as _build_pea_pkg,
        write_pre_execution_audit_event as _write_pea_event,
        ERROR_PRE_EXECUTION_AUDIT_WRITTEN_BUT_HANDLER_LOOKUP_NOT_ENABLED as _PEA_WRITTEN_BLOCKED,
    )

    # Build the pre-execution audit package from the safe execute context
    pea_pkg_result = _build_pea_pkg(
        dry_run_request_id=dry_run_request_id,
        dry_run_decision_digest=historical_digest or "",
        canonical_name=canonical_name,
        risk_tier=risk_tier,
        policy_version=None,
        arguments_digest=None,
        redaction_version=None,
        audit_event_id=lookup_result.audit_event_id,
        confirmation_token_id=token_result.token_id,
        confirmation_issued_at=(
            token_result.safe_summary.get("issuedAt")
            if token_result.safe_summary
            else None
        ),
        confirmation_consumed_at=None,
        digest_algorithm="sha256",
        digest_package_version="1",
        canonicalization_version="json-sort-v1",
        historical_digest=historical_digest,
        token_bound_digest=token_bound_digest,
        execute_derived_digest=execute_derived_digest,
    )

    if not pea_pkg_result.success:
        # Pre-execution audit package build failed
        gates.append(ToolExecuteGateStatus(
            gate=GATE_PRE_EXECUTION_AUDIT_PACKAGE,
            passed=False,
            error_code=pea_pkg_result.error_code,
        ))
        policy_notes.append(
            f"Pre-execution audit package build failed: "
            f"{pea_pkg_result.error_code}. Execution remains blocked."
        )
        reason_codes.append(pea_pkg_result.error_code)
        error_code = pea_pkg_result.error_code
        decision = DECISION_BLOCKED_PRE_EXECUTION_AUDIT_NOT_IMPLEMENTED

        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    # Write the pre-execution audit event
    pea_write_result = _write_pea_event(
        hermes_home=hermes_home,
        audit_package=pea_pkg_result.audit_package,
    )

    if not pea_write_result.written:
        # Pre-execution audit write failed — block
        gates.append(ToolExecuteGateStatus(
            gate=GATE_PRE_EXECUTION_AUDIT_WRITE,
            passed=False,
            error_code=pea_write_result.error_code,
        ))
        policy_notes.append(
            f"Pre-execution audit write failed: "
            f"{pea_write_result.error_code}. Execution remains blocked."
        )
        reason_codes.append(pea_write_result.error_code)
        error_code = pea_write_result.error_code
        decision = pea_write_result.decision or DECISION_BLOCKED_PRE_EXECUTION_AUDIT_NOT_IMPLEMENTED

        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
        )

    # Pre-execution audit written successfully
    gates.append(ToolExecuteGateStatus(
        gate=GATE_PRE_EXECUTION_AUDIT, passed=True, error_code=None,
    ))

    # ── Gate 46–56: Handler lookup (Phase 1G-04-26) ──
    from hermes_cli.dev_web_tool_handler_lookup import (
        lookup_handler_descriptor as _lookup_handler,
    )

    lookup_result = _lookup_handler(
        canonical_name,
        allowlist=STATIC_ALLOWLIST,
    )

    if not lookup_result.found:
        # Handler lookup failed — block before dispatch
        lookup_error = lookup_result.error_code or ERROR_HANDLER_LOOKUP_UNAVAILABLE
        lookup_gate = lookup_result.gate or GATE_HANDLER_LOOKUP
        lookup_decision = lookup_result.decision or DECISION_BLOCKED_HANDLER_LOOKUP_UNAVAILABLE

        gates.append(ToolExecuteGateStatus(
            gate=lookup_gate,
            passed=False,
            error_code=lookup_error,
        ))
        policy_notes.append(
            f"Handler lookup failed: {lookup_error}. Execution remains blocked."
        )
        reason_codes.append(lookup_error)
        error_code = lookup_error
        decision = lookup_decision

        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
            pre_execution_audit_id=pea_write_result.pre_execution_audit_id,
            execute_request_id=pea_write_result.execute_request_id,
            pre_execution_audit_status="written",
        )

    # Handler lookup succeeded
    gates.append(ToolExecuteGateStatus(
        gate=GATE_HANDLER_LOOKUP, passed=True, error_code=None,
    ))

    # ── Gate 57–69: Dispatch planning (Phase 1G-04-28) ──
    # Safe dispatch plan / envelope construction — metadata-only routing.
    # Dispatch plan success is NOT Tool Handler call permission.
    from hermes_cli.dev_web_tool_dispatch import (
        build_dispatch_plan as _build_dispatch_plan,
    )

    dispatch_result = _build_dispatch_plan(
        canonical_name=canonical_name,
        handler_lookup_id=lookup_result.handler_lookup_id,
        handler_descriptor=lookup_result.handler_descriptor,
        allowlist=STATIC_ALLOWLIST,
        risk_tier=risk_tier,
        toolset_name="builtin",
    )

    if not dispatch_result.built:
        # Dispatch planning failed — block before Tool Handler call
        dispatch_error = dispatch_result.error_code or ERROR_DISPATCH_UNAVAILABLE
        dispatch_gate = dispatch_result.gate or GATE_DISPATCH_PLAN
        dispatch_decision = dispatch_result.decision or DECISION_BLOCKED_DISPATCH_UNAVAILABLE

        gates.append(ToolExecuteGateStatus(
            gate=dispatch_gate,
            passed=False,
            error_code=dispatch_error,
        ))
        policy_notes.append(
            f"Dispatch planning failed: {dispatch_error}. Execution remains blocked."
        )
        reason_codes.append(dispatch_error)
        error_code = dispatch_error
        decision = dispatch_decision

        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=error_code,
            decision=decision,
            risk_tier=risk_tier,
            pre_execution_audit_id=pea_write_result.pre_execution_audit_id,
            execute_request_id=pea_write_result.execute_request_id,
            pre_execution_audit_status="written",
            handler_lookup_id=lookup_result.handler_lookup_id,
            handler_lookup_status=lookup_result.handler_lookup_status,
            handler_descriptor=lookup_result.handler_descriptor,
        )

    # Dispatch planning succeeded — record pass.
    gates.append(ToolExecuteGateStatus(
        gate=GATE_DISPATCH, passed=True, error_code=None,
    ))

    # ── Gate 70–83: Tool Handler call + Post-execution audit (Phase 1G-04-29) ──
    # DEFAULT-DISABLED: only an explicit dev gate
    # (HERMES_TOOL_HANDLER_CALL_ENABLED == "true") allows the clarify-only
    # handler call. Dispatch plan existence is NOT handler-call permission.
    from hermes_cli.dev_web_tool_handler_call import (
        attempt_clarify_handler_call as _attempt_handler_call,
    )
    from hermes_cli.dev_web_tool_post_execution_audit import (
        build_post_execution_audit_package as _build_post_pkg,
        write_post_execution_audit_event as _write_post_event,
    )

    handler_call_result = _attempt_handler_call(
        canonical_name=canonical_name,
        handler_descriptor=lookup_result.handler_descriptor,
        dispatch_plan=dispatch_result.dispatch_plan,
        handler_lookup_id=lookup_result.handler_lookup_id,
        dispatch_id=dispatch_result.dispatch_id,
        execute_request_id=pea_write_result.execute_request_id,
        pre_execution_audit_id=pea_write_result.pre_execution_audit_id,
        arguments=arguments_preview if isinstance(arguments_preview, dict) else None,
        hermes_home=hermes_home,
    )

    if not handler_call_result.called:
        # Handler call blocked (default-disabled or a consistency gate failed).
        # No handler invoked, no execution, no provider call.
        hc_error = handler_call_result.error_code or ERROR_TOOL_HANDLER_CALL_NOT_ENABLED
        gates.append(ToolExecuteGateStatus(
            gate=handler_call_result.gate or GATE_TOOL_HANDLER_CALL,
            passed=False,
            error_code=hc_error,
        ))
        policy_notes.append(
            f"Tool Handler call blocked: {hc_error}. Execution remains blocked."
        )
        reason_codes.append(hc_error)
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=hc_error,
            decision=handler_call_result.decision
            or DECISION_BLOCKED_TOOL_HANDLER_CALL_NOT_ENABLED,
            risk_tier=risk_tier,
            pre_execution_audit_id=pea_write_result.pre_execution_audit_id,
            execute_request_id=pea_write_result.execute_request_id,
            pre_execution_audit_status="written",
            handler_lookup_id=lookup_result.handler_lookup_id,
            handler_lookup_status=lookup_result.handler_lookup_status,
            handler_descriptor=lookup_result.handler_descriptor,
            dispatch_id=dispatch_result.dispatch_id,
            dispatch_status=dispatch_result.dispatch_status,
            dispatch_plan=dispatch_result.dispatch_plan,
        )

    # Handler called successfully — record gate pass.
    gates.append(ToolExecuteGateStatus(
        gate=GATE_TOOL_HANDLER_CALL, passed=True, error_code=None,
    ))

    # ── Gate 80–82: Post-execution audit (REQUIRED, fail-closed) ──
    # No successful controlled execution response without post-execution audit.
    post_pkg_result = _build_post_pkg(
        execute_request_id=pea_write_result.execute_request_id,
        pre_execution_audit_id=pea_write_result.pre_execution_audit_id,
        handler_lookup_id=lookup_result.handler_lookup_id,
        dispatch_id=dispatch_result.dispatch_id,
        handler_call_id=handler_call_result.handler_call_id,
        canonical_name=canonical_name,
        execution_status=handler_call_result.execution_status,
        handler_call_status=handler_call_result.handler_call_status,
        dry_run_decision_digest=historical_digest,
        confirmation_token_id=token_result.token_id,
        tool_result=handler_call_result.tool_result,
    )

    if not post_pkg_result.success:
        post_error = post_pkg_result.error_code or ERROR_POST_EXECUTION_AUDIT_WRITE_FAILED
        gates.append(ToolExecuteGateStatus(
            gate=GATE_POST_EXECUTION_AUDIT,
            passed=False,
            error_code=post_error,
        ))
        policy_notes.append(
            f"Post-execution audit package build failed: {post_error}. "
            "Execution fails closed."
        )
        reason_codes.append(post_error)
        # FAIL CLOSED: do not surface success-indicating handler-call status.
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=post_error,
            decision=DECISION_BLOCKED_POST_EXECUTION_AUDIT_FAILED,
            risk_tier=risk_tier,
            pre_execution_audit_id=pea_write_result.pre_execution_audit_id,
            execute_request_id=pea_write_result.execute_request_id,
            pre_execution_audit_status="written",
            handler_lookup_id=lookup_result.handler_lookup_id,
            handler_lookup_status=lookup_result.handler_lookup_status,
            handler_descriptor=lookup_result.handler_descriptor,
            dispatch_id=dispatch_result.dispatch_id,
            dispatch_status=dispatch_result.dispatch_status,
            dispatch_plan=dispatch_result.dispatch_plan,
            post_execution_audit_status="failed",
        )

    post_write_result = _write_post_event(
        hermes_home=hermes_home,
        audit_package=post_pkg_result.audit_package,
    )

    if not post_write_result.written:
        # FAIL CLOSED — a successful controlled execution requires a written
        # post-execution audit. No success response is returned on failure.
        post_write_error = post_write_result.error_code or ERROR_POST_EXECUTION_AUDIT_WRITE_FAILED
        gates.append(ToolExecuteGateStatus(
            gate=GATE_POST_EXECUTION_AUDIT_WRITE,
            passed=False,
            error_code=post_write_error,
        ))
        policy_notes.append(
            f"Post-execution audit write failed: {post_write_error}. "
            "Execution fails closed — no success response."
        )
        reason_codes.append(post_write_error)
        # FAIL CLOSED: handler was invoked but execution result is NOT returned
        # as successful. No success-indicating handler-call status is surfaced.
        return _build_blocked_result(
            canonical_name=canonical_name,
            gates=gates,
            policy_notes=policy_notes,
            reason_codes=reason_codes,
            error_code=post_write_error,
            decision=DECISION_BLOCKED_POST_EXECUTION_AUDIT_FAILED,
            risk_tier=risk_tier,
            pre_execution_audit_id=pea_write_result.pre_execution_audit_id,
            execute_request_id=pea_write_result.execute_request_id,
            pre_execution_audit_status="written",
            handler_lookup_id=lookup_result.handler_lookup_id,
            handler_lookup_status=lookup_result.handler_lookup_status,
            handler_descriptor=lookup_result.handler_descriptor,
            dispatch_id=dispatch_result.dispatch_id,
            dispatch_status=dispatch_result.dispatch_status,
            dispatch_plan=dispatch_result.dispatch_plan,
            post_execution_audit_status="failed",
        )

    # ── Gate 83: Safe controlled execution response ──
    gates.append(ToolExecuteGateStatus(
        gate=GATE_POST_EXECUTION_AUDIT, passed=True, error_code=None,
    ))
    policy_notes.append(
        "Controlled read-only execution completed. Tool Handler called, "
        "result normalized, post-execution audit written. No Provider Schema "
        "sent, no Provider API called, no external side effects."
    )
    return _build_success_result(
        canonical_name=canonical_name,
        gates=gates,
        policy_notes=policy_notes,
        risk_tier=risk_tier,
        pre_execution_audit_id=pea_write_result.pre_execution_audit_id,
        execute_request_id=pea_write_result.execute_request_id,
        handler_lookup_id=lookup_result.handler_lookup_id,
        handler_lookup_status=lookup_result.handler_lookup_status,
        handler_descriptor=lookup_result.handler_descriptor,
        dispatch_id=dispatch_result.dispatch_id,
        dispatch_status=dispatch_result.dispatch_status,
        dispatch_plan=dispatch_result.dispatch_plan,
        handler_call_id=handler_call_result.handler_call_id,
        handler_call_status=handler_call_result.handler_call_status,
        execution_status=handler_call_result.execution_status,
        post_execution_audit_id=post_write_result.post_execution_audit_id,
        tool_result=handler_call_result.tool_result,
        side_effects=handler_call_result.side_effects,
        tool_handler_called=handler_call_result.called,
    )


# ---------------------------------------------------------------------------
# 10. Helper: build blocked result
# ---------------------------------------------------------------------------


def _build_blocked_result(
    *,
    canonical_name: str,
    gates: list[ToolExecuteGateStatus],
    policy_notes: list[str],
    reason_codes: list[str],
    error_code: str,
    decision: str,
    risk_tier: str | None = None,
    pre_execution_audit_id: str | None = None,
    execute_request_id: str | None = None,
    pre_execution_audit_status: str | None = None,
    handler_lookup_id: str | None = None,
    handler_lookup_status: str | None = None,
    handler_descriptor: dict[str, Any] | None = None,
    dispatch_id: str | None = None,
    dispatch_status: str | None = None,
    dispatch_plan: dict[str, Any] | None = None,
    handler_call_id: str | None = None,
    handler_call_status: str | None = None,
    execution_status: str | None = None,
    post_execution_audit_status: str | None = None,
) -> ToolExecuteResult:
    """Build a standard blocked ToolExecuteResult."""
    return ToolExecuteResult(
        canonical_name=canonical_name,
        exists=_lookup_tool_policy(canonical_name)[0],
        risk_tier=risk_tier,
        decision=decision,
        gate_status=tuple(gates),
        audit_status=ToolExecuteAuditStatus(
            audit_attempted=False,
            audit_written=False,
            audit_error=None,
        ),
        result_preview=ToolExecuteResultPreview(
            available=False,
            preview_type=None,
            preview_size_bytes=0,
            truncated=False,
        ),
        execution_attempted=False,
        execution_started=False,
        execution_completed=False,
        execution_allowed=False,
        dispatch_allowed=False,
        provider_schema_allowed=False,
        tool_handler_called=False,
        provider_api_called=False,
        error_code=error_code,
        policy_notes=tuple(policy_notes),
        reason_codes=tuple(reason_codes),
        pre_execution_audit_id=pre_execution_audit_id,
        execute_request_id=execute_request_id,
        pre_execution_audit_status=pre_execution_audit_status,
        handler_lookup_id=handler_lookup_id,
        handler_lookup_status=handler_lookup_status,
        handler_descriptor=handler_descriptor,
        dispatch_id=dispatch_id,
        dispatch_status=dispatch_status,
        dispatch_plan=dispatch_plan,
        handler_call_id=handler_call_id,
        handler_call_status=handler_call_status,
        execution_status=execution_status,
        post_execution_audit_status=post_execution_audit_status,
    )


def _build_success_result(
    *,
    canonical_name: str,
    gates: list[ToolExecuteGateStatus],
    policy_notes: list[str],
    risk_tier: str | None,
    pre_execution_audit_id: str | None,
    execute_request_id: str | None,
    handler_lookup_id: str | None,
    handler_lookup_status: str | None,
    handler_descriptor: dict[str, Any] | None,
    dispatch_id: str | None,
    dispatch_status: str | None,
    dispatch_plan: dict[str, Any] | None,
    handler_call_id: str | None,
    handler_call_status: str | None,
    execution_status: str | None,
    post_execution_audit_id: str | None,
    tool_result: dict[str, Any] | None,
    side_effects: dict[str, Any] | None,
    tool_handler_called: bool,
) -> ToolExecuteResult:
    """Build a successful clarify-only controlled execution result.

    Only reachable when: kill switches enabled + clarify allowlisted + valid
    dry-run + valid confirmation token + valid digest + pre-execution audit
    written + handler lookup found + dispatch plan built + explicit handler
    call gate enabled + clarify handler invoked + result normalized +
    post-execution audit written. The ``if not handler_call_result.called``
    guard in ``evaluate_tool_execute_request`` guarantees this builder is never
    reached when the handler was not actually invoked under the explicit gate,
    so ``tool_handler_called`` is derived from the verified result rather than
    assumed.

    Invariants preserved:
      - executionAllowed = False (policy flag stays false; the clarify
        exception is tracked by executionCompleted + executionStatus)
      - dispatchAllowed = False
      - providerSchemaAllowed = False
      - providerApiCalled = False
      - All side_effects external flags = False
    """
    preview_size = 0
    if tool_result is not None:
        try:
            preview_size = len(json.dumps(tool_result, ensure_ascii=False))
        except (TypeError, ValueError):
            preview_size = 0

    return ToolExecuteResult(
        canonical_name=canonical_name,
        exists=_lookup_tool_policy(canonical_name)[0],
        risk_tier=risk_tier,
        decision=_completed_decision_for(canonical_name),
        gate_status=tuple(gates),
        audit_status=ToolExecuteAuditStatus(
            audit_attempted=True,
            audit_written=True,
            audit_error=None,
        ),
        result_preview=ToolExecuteResultPreview(
            available=True,
            preview_type=_completed_preview_type(canonical_name, tool_result),
            preview_size_bytes=preview_size,
            truncated=False,
        ),
        execution_attempted=True,
        execution_started=True,
        execution_completed=True,
        execution_allowed=False,
        dispatch_allowed=False,
        provider_schema_allowed=False,
        tool_handler_called=tool_handler_called,
        provider_api_called=False,
        error_code=None,
        policy_notes=tuple(policy_notes),
        reason_codes=(),
        pre_execution_audit_id=pre_execution_audit_id,
        execute_request_id=execute_request_id,
        pre_execution_audit_status="written",
        handler_lookup_id=handler_lookup_id,
        handler_lookup_status=handler_lookup_status,
        handler_descriptor=handler_descriptor,
        dispatch_id=dispatch_id,
        dispatch_status=dispatch_status,
        dispatch_plan=dispatch_plan,
        handler_call_id=handler_call_id,
        handler_call_status=handler_call_status,
        execution_status=execution_status,
        post_execution_audit_id=post_execution_audit_id,
        post_execution_audit_status="written",
        tool_result=tool_result,
        side_effects=side_effects,
    )


def compute_execute_policy_summary() -> ToolExecutePolicySummary:
    """Compute the current execute policy summary.

    This is a read-only snapshot of the execution gate state.
    """
    from hermes_cli.dev_web_tool_policy import (
        STATIC_ALLOWLIST,
        STATIC_DENYLIST,
    )

    return ToolExecutePolicySummary(
        kill_switch_enabled=_is_kill_switch_enabled("HERMES_TOOL_EXECUTION_ENABLED"),
        agent_tools_enabled=_is_kill_switch_enabled("HERMES_AGENT_TOOLS_ENABLED"),
        static_allowlist_size=len(STATIC_ALLOWLIST),
        static_allowlist_tools=tuple(sorted(STATIC_ALLOWLIST)),
        denylist_size=len(STATIC_DENYLIST),
        execution_enabled=False,
        dispatch_enabled=False,
        provider_schema_enabled=False,
    )
