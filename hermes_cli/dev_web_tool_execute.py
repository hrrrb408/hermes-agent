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

Phase: 1G-04-11 — Backend Execute Gate Skeleton
Status: Blocked-only (no real tool execution)
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
ERROR_DIGEST_MISMATCH = "digest_mismatch"
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
GATE_CONFIRMATION = "confirmation"
GATE_DIGEST = "digest"
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

    def to_safe_dict(self) -> dict[str, Any]:
        """Convert to JSON-safe dict with all execution flags false."""
        return {
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
) -> ToolExecuteResult:
    """Evaluate a tool execute request through the gate stack.

    This function is **blocked-only** in Phase 1G-04-11.
    Every request returns a blocked response with all execution flags false.
    No tool handler is called, no dispatch occurs, no provider is contacted.

    Gate evaluation order:
      1. Kill switch (HERMES_TOOL_EXECUTION_ENABLED)
      2. Agent tools switch (HERMES_AGENT_TOOLS_ENABLED)
      3. Static allowlist (must be non-empty)
      4. Known tool (must exist in inventory)
      5. Denylist (must not be denylisted)
      6. Risk tier (R0/R1 only eligible in future)
      7. Dry-run preflight (must have prior dry-run)
      8. Dry-run digest (must match)
      9. Confirmation token (must be present)
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
            "Dry-run historical lookup is a future phase."
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

    if not dry_run_decision_digest:
        gates.append(ToolExecuteGateStatus(
            gate=GATE_DRY_RUN_PREFLIGHT,
            passed=False,
            error_code=ERROR_DRY_RUN_DIGEST_MISSING,
        ))
        policy_notes.append(
            "Dry-run decision digest is required. "
            "Digest verification is a future phase."
        )
        reason_codes.append(ERROR_DRY_RUN_DIGEST_MISSING)
        error_code = ERROR_DRY_RUN_DIGEST_MISSING
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

    # ── Gate 8: Digest validation (skeleton) ──
    # In this phase, we accept any non-empty digest — real validation is future
    # But we still block because confirmation token is needed
    gates.append(ToolExecuteGateStatus(
        gate=GATE_DIGEST, passed=True, error_code=None,
    ))

    # ── Gate 9: Confirmation token ──
    if not confirmation_token:
        gates.append(ToolExecuteGateStatus(
            gate=GATE_CONFIRMATION,
            passed=False,
            error_code=ERROR_CONFIRMATION_MISSING,
        ))
        policy_notes.append(
            "Confirmation token is required before execution. "
            "Token issuance is a future phase."
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

    # Even with confirmation token, in this phase we still block
    # because no real handler exists and execution is not implemented
    gates.append(ToolExecuteGateStatus(
        gate=GATE_CONFIRMATION, passed=True, error_code=None,
    ))
    policy_notes.append(
        "All gates passed but execution is not implemented in this phase. "
        "Blocked by skeleton implementation."
    )
    reason_codes.append("EXECUTION_NOT_IMPLEMENTED")
    error_code = "execution_not_implemented"
    decision = DECISION_BLOCKED

    return _build_blocked_result(
        canonical_name=canonical_name,
        gates=gates,
        policy_notes=policy_notes,
        reason_codes=reason_codes,
        error_code=error_code,
        decision=decision,
        risk_tier=risk_tier,
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
    )


# ---------------------------------------------------------------------------
# 11. Policy summary
# ---------------------------------------------------------------------------


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
