"""Tool Dry-Run Policy Model for the Hermes Dev WebUI.

This module implements a pure-function dry-run decision engine that evaluates
whether a proposed tool call would be allowed, blocked, redacted, or require
review — **without invoking any tool handler, provider, or runtime service**.

Architecture constraints:
  - stdlib only (no third-party imports)
  - import side effects = 0 (beyond importing static policy constants)
  - no file IO, no network IO, no environment reads
  - no provider imports, no tool handler imports, no runtime DB access
  - no memory access, no review queue access
  - deterministic, JSON-serializable output
  - type hints, frozen dataclasses, explicit constants
  - execution_allowed is ALWAYS False in this phase
  - dispatch_allowed is ALWAYS False in this phase
  - provider_schema_allowed is ALWAYS False in this phase
  - audit_written is ALWAYS False in this phase

Phase: 1G-04-01 — Dry-Run Policy Service Model
Status: Pure model (no API, no OpenAPI, no frontend)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from hermes_cli.dev_web_tool_policy import (
    ALL_CANONICAL_TOOLS,
    CANDIDATE_ALLOWLIST,
    RISK_RANK,
    STATIC_ALLOWLIST,
    STATIC_DENYLIST,
    TOOL_POLICY_INVENTORY,
    ToolPolicyEntry,
    ToolRiskLevel,
    get_tool_policy,
)


# ---------------------------------------------------------------------------
# 1. Dry-Run Decision constants
# ---------------------------------------------------------------------------

DRY_RUN_DECISION_WOULD_ALLOW = "would_allow"
DRY_RUN_DECISION_WOULD_BLOCK = "would_block"
DRY_RUN_DECISION_WOULD_REDACT = "would_redact"
DRY_RUN_DECISION_REQUIRES_REVIEW = "requires_review"


# ---------------------------------------------------------------------------
# 2. Reason codes
# ---------------------------------------------------------------------------

# would_allow reasons
WOULD_ALLOW_STATIC_POLICY = "WOULD_ALLOW_STATIC_POLICY"
DRY_RUN_ONLY_NO_EXECUTION = "DRY_RUN_ONLY_NO_EXECUTION"

# would_block reasons
WOULD_BLOCK_UNKNOWN_TOOL = "WOULD_BLOCK_UNKNOWN_TOOL"
WOULD_BLOCK_DENYLISTED = "WOULD_BLOCK_DENYLISTED"
WOULD_BLOCK_R4_EXECUTION_RISK = "WOULD_BLOCK_R4_EXECUTION_RISK"
WOULD_BLOCK_R5_SYSTEM_RISK = "WOULD_BLOCK_R5_SYSTEM_RISK"
WOULD_BLOCK_STATIC_ALLOWLIST_EMPTY = "WOULD_BLOCK_STATIC_ALLOWLIST_EMPTY"
WOULD_BLOCK_EXECUTION_DISABLED = "WOULD_BLOCK_EXECUTION_DISABLED"

# would_redact reasons
WOULD_REDACT_SECRET_PATTERN = "WOULD_REDACT_SECRET_PATTERN"
WOULD_REDACT_FORBIDDEN_FIELD = "WOULD_REDACT_FORBIDDEN_FIELD"

# requires_review reasons
REQUIRES_REVIEW_R2 = "REQUIRES_REVIEW_R2"
REQUIRES_REVIEW_R3 = "REQUIRES_REVIEW_R3"
REQUIRES_REVIEW_CANDIDATE_ONLY = "REQUIRES_REVIEW_CANDIDATE_ONLY"
REQUIRES_REVIEW_ARGUMENTS_PRESENT = "REQUIRES_REVIEW_ARGUMENTS_PRESENT"
REQUIRES_REVIEW_SCHEMA_UNAVAILABLE = "REQUIRES_REVIEW_SCHEMA_UNAVAILABLE"

# structural
INVALID_ARGUMENT_SHAPE = "INVALID_ARGUMENT_SHAPE"


# ---------------------------------------------------------------------------
# 3. Argument sanitization limits
# ---------------------------------------------------------------------------

MAX_ARGUMENT_DEPTH: int = 4
MAX_ARGUMENT_FIELDS: int = 100
MAX_ARGUMENT_STRING_CHARS: int = 160
MAX_ARGUMENT_LIST_ITEMS: int = 20

_REDACTED_VALUE = "[REDACTED]"
_TRUNCATED_SUFFIX = "…"


# ---------------------------------------------------------------------------
# 4. Secret pattern detection for argument values
# ---------------------------------------------------------------------------

_SECRET_KEY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(api_key|apikey|token|secret|password|authorization|cookie|"
        r"credential|bearer|private_key|access_key|refresh_token|client_secret|"
        r"access_token|auth_header|passwd|session)",
        re.IGNORECASE,
    ),
)

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

# Normalized forbidden names for case-insensitive matching
_NORMALIZED_FORBIDDEN_ARG_FIELDS: frozenset[str] = frozenset(
    n.replace("_", "").replace("-", "").lower() for n in _FORBIDDEN_ARG_FIELD_NAMES
)


def _normalize_field_name(name: str) -> str:
    """Normalize a field name for comparison (strip underscores/hyphens, lower)."""
    return name.replace("_", "").replace("-", "").lower()


def _is_secret_key(key: str) -> bool:
    """Check if a field name looks like a secret/credential key."""
    return _normalize_field_name(key) in _NORMALIZED_FORBIDDEN_ARG_FIELDS


def _is_secret_value(value: str) -> bool:
    """Check if a string value matches known secret patterns."""
    for pattern in _SECRET_VALUE_PATTERNS:
        if pattern.search(value):
            return True
    return False


# ---------------------------------------------------------------------------
# 5. Arguments sanitizer
# ---------------------------------------------------------------------------


def sanitize_arguments_preview(
    arguments: Mapping[str, Any] | Any,
    *,
    max_depth: int = MAX_ARGUMENT_DEPTH,
    max_fields: int = MAX_ARGUMENT_FIELDS,
    max_string_chars: int = MAX_ARGUMENT_STRING_CHARS,
    max_list_items: int = MAX_ARGUMENT_LIST_ITEMS,
) -> tuple[dict[str, Any], tuple[str, ...], tuple[str, ...]]:
    """Sanitize proposed arguments for safe dry-run preview.

    Returns:
        (redacted_dict, forbidden_fields, reason_codes)

    Guarantees:
        - No raw secrets in output
        - No excessive nesting
        - No extremely long strings
        - Forbidden fields redacted
        - JSON-safe output
    """
    forbidden_fields: list[str] = []
    reason_codes: list[str] = []

    # Handle non-mapping
    if arguments is None:
        return {}, (), ()
    if not isinstance(arguments, Mapping):
        reason_codes.append(INVALID_ARGUMENT_SHAPE)
        return {}, (), tuple(reason_codes)

    result = _sanitize_mapping(
        arguments,
        path="",
        depth=0,
        max_depth=max_depth,
        max_fields=max_fields,
        max_string_chars=max_string_chars,
        max_list_items=max_list_items,
        forbidden_fields=forbidden_fields,
        reason_codes=reason_codes,
    )

    return result, tuple(forbidden_fields), tuple(reason_codes)


def _sanitize_mapping(
    data: Mapping[str, Any],
    *,
    path: str,
    depth: int,
    max_depth: int,
    max_fields: int,
    max_string_chars: int,
    max_list_items: int,
    forbidden_fields: list[str],
    reason_codes: list[str],
) -> dict[str, Any]:
    """Recursively sanitize a mapping."""
    result: dict[str, Any] = {}
    count = 0

    for key, value in data.items():
        if count >= max_fields:
            break
        count += 1

        field_path = f"{path}.{key}" if path else key

        # Check forbidden field name
        if _is_secret_key(key):
            forbidden_fields.append(field_path)
            reason_codes.append(WOULD_REDACT_SECRET_PATTERN)
            result[key] = _REDACTED_VALUE
            continue

        result[key] = _sanitize_value(
            value,
            path=field_path,
            depth=depth,
            max_depth=max_depth,
            max_string_chars=max_string_chars,
            max_list_items=max_list_items,
            forbidden_fields=forbidden_fields,
            reason_codes=reason_codes,
        )

    return result


def _sanitize_value(
    value: Any,
    *,
    path: str,
    depth: int,
    max_depth: int,
    max_string_chars: int,
    max_list_items: int,
    forbidden_fields: list[str],
    reason_codes: list[str],
) -> Any:
    """Sanitize a single value."""
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return value

    if isinstance(value, str):
        if _is_secret_value(value):
            reason_codes.append(WOULD_REDACT_SECRET_PATTERN)
            return _REDACTED_VALUE
        if len(value) > max_string_chars:
            return value[:max_string_chars] + _TRUNCATED_SUFFIX
        return value

    if isinstance(value, Mapping):
        if depth >= max_depth:
            reason_codes.append(WOULD_REDACT_FORBIDDEN_FIELD)
            forbidden_fields.append(path)
            return {"_truncated": "nested structure exceeds depth limit"}
        return _sanitize_mapping(
            value,
            path=path,
            depth=depth + 1,
            max_depth=max_depth,
            max_fields=MAX_ARGUMENT_FIELDS,
            max_string_chars=max_string_chars,
            max_list_items=max_list_items,
            forbidden_fields=forbidden_fields,
            reason_codes=reason_codes,
        )

    if isinstance(value, (list, tuple)):
        if len(value) > max_list_items:
            truncated = list(value[:max_list_items])
            truncated.append(f"… ({len(value) - max_list_items} more items)")
            return [
                _sanitize_value(
                    item,
                    path=f"{path}[{i}]",
                    depth=depth,
                    max_depth=max_depth,
                    max_string_chars=max_string_chars,
                    max_list_items=max_list_items,
                    forbidden_fields=forbidden_fields,
                    reason_codes=reason_codes,
                )
                for i, item in enumerate(truncated)
            ]
        return [
            _sanitize_value(
                item,
                path=f"{path}[{i}]",
                depth=depth,
                max_depth=max_depth,
                max_string_chars=max_string_chars,
                max_list_items=max_list_items,
                forbidden_fields=forbidden_fields,
                reason_codes=reason_codes,
            )
            for i, item in enumerate(value)
        ]

    # Unknown type → string representation, truncated
    try:
        s = str(value)
        if len(s) > max_string_chars:
            return s[:max_string_chars] + _TRUNCATED_SUFFIX
        return s
    except Exception:
        return "[unsupported type]"


# ---------------------------------------------------------------------------
# 6. Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolDryRunRequest:
    """Immutable dry-run request DTO.

    Attributes:
        canonical_name: Exact tool canonical name.
        arguments_preview: Proposed arguments (may be partial, empty, or None).
            Never store raw secrets; input is sanitized by the engine.
        source_context: Optional source context description.
        ui_origin: Optional UI component identifier.
    """

    canonical_name: str
    arguments_preview: Mapping[str, Any] | None = None
    source_context: str | None = None
    ui_origin: str | None = None


@dataclass(frozen=True, slots=True)
class ToolDryRunResult:
    """Immutable dry-run result DTO.

    Invariants (Phase 1G-04-01):
        - execution_allowed is ALWAYS False
        - dispatch_allowed is ALWAYS False
        - provider_schema_allowed is ALWAYS False
        - audit_written is ALWAYS False

    Attributes:
        canonical_name: Tool canonical name (or the requested name if unknown).
        exists: Whether the tool exists in the policy inventory.
        risk_tier: Risk tier string (e.g. "R0") or None if unknown.
        decision: One of the DRY_RUN_DECISION_* constants.
        reason_codes: Machine-readable reason codes for the decision.
        policy_notes: Human-readable policy notes.
        redacted_arguments_preview: Sanitized arguments with secrets redacted.
        forbidden_fields: Field paths that were redacted.
        missing_required_fields: Placeholder for future schema validation.
        execution_allowed: Always False in this phase.
        dispatch_allowed: Always False in this phase.
        provider_schema_allowed: Always False in this phase.
        audit_written: Always False in this phase.
    """

    canonical_name: str
    exists: bool
    risk_tier: str | None
    decision: str
    reason_codes: tuple[str, ...]
    policy_notes: tuple[str, ...]
    redacted_arguments_preview: dict[str, Any]
    forbidden_fields: tuple[str, ...]
    missing_required_fields: tuple[str, ...]
    execution_allowed: bool
    dispatch_allowed: bool
    provider_schema_allowed: bool
    audit_written: bool

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation."""
        return {
            "canonicalName": self.canonical_name,
            "exists": self.exists,
            "riskTier": self.risk_tier,
            "decision": self.decision,
            "reasonCodes": list(self.reason_codes),
            "policyNotes": list(self.policy_notes),
            "redactedArgumentsPreview": self.redacted_arguments_preview,
            "forbiddenFields": list(self.forbidden_fields),
            "missingRequiredFields": list(self.missing_required_fields),
            "executionAllowed": self.execution_allowed,
            "dispatchAllowed": self.dispatch_allowed,
            "providerSchemaAllowed": self.provider_schema_allowed,
            "auditWritten": self.audit_written,
        }


@dataclass(frozen=True, slots=True)
class ToolDryRunPolicySummary:
    """Aggregate summary of dry-run policy across all tools.

    Attributes:
        total_count: Total tools in inventory.
        dry_run_allow_count: Tools that would be allowed for dry-run simulation.
        blocked_count: Tools that would be blocked.
        review_count: Tools that require review.
        redacted_count: Tools that would require argument redaction.
    """

    total_count: int
    dry_run_allow_count: int
    blocked_count: int
    review_count: int
    redacted_count: int

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation."""
        return {
            "totalCount": self.total_count,
            "dryRunAllowCount": self.dry_run_allow_count,
            "blockedCount": self.blocked_count,
            "reviewCount": self.review_count,
            "redactedCount": self.redacted_count,
        }


# ---------------------------------------------------------------------------
# 7. Core dry-run policy engine
# ---------------------------------------------------------------------------


def _merge_reason_codes(
    policy_reasons: list[str],
    arg_reasons: tuple[str, ...],
) -> tuple[str, ...]:
    """Merge policy reason codes with argument sanitization reason codes.

    Deduplicates while preserving order.
    """
    seen: set[str] = set()
    merged: list[str] = []
    for code in policy_reasons:
        if code not in seen:
            seen.add(code)
            merged.append(code)
    for code in arg_reasons:
        if code not in seen:
            seen.add(code)
            merged.append(code)
    return tuple(merged)


def dry_run_tool_policy(
    canonical_name: str,
    arguments_preview: Mapping[str, Any] | None = None,
    *,
    source_context: str | None = None,
    ui_origin: str | None = None,
) -> ToolDryRunResult:
    """Evaluate dry-run policy for a proposed tool call.

    This is the main entry point. It:
      1. Looks up the tool in the static policy inventory
      2. Applies risk-tier rules to determine decision
      3. Sanitizes proposed arguments
      4. Returns a frozen ToolDryRunResult

    Guarantees:
      - Does NOT call any tool handler
      - Does NOT call any provider
      - Does NOT access runtime state
      - Does NOT write audit records
      - Does NOT read .env or ~/.hermes
      - Does NOT modify global state
      - execution_allowed is ALWAYS False
      - dispatch_allowed is ALWAYS False
      - provider_schema_allowed is ALWAYS False
      - audit_written is ALWAYS False

    Args:
        canonical_name: Exact tool canonical name.
        arguments_preview: Optional proposed arguments mapping.
        source_context: Optional source context description.
        ui_origin: Optional UI component identifier.

    Returns:
        Immutable ToolDryRunResult with the dry-run decision.
    """
    # Step 1: Sanitize arguments
    redacted_args, forbidden_fields, arg_reason_codes = sanitize_arguments_preview(
        arguments_preview,
    )

    # Step 2: Look up tool in inventory
    entry = get_tool_policy(canonical_name)

    if entry is None:
        # Unknown tool
        return ToolDryRunResult(
            canonical_name=canonical_name,
            exists=False,
            risk_tier=None,
            decision=DRY_RUN_DECISION_WOULD_BLOCK,
            reason_codes=_merge_reason_codes(
                [WOULD_BLOCK_UNKNOWN_TOOL], arg_reason_codes
            ),
            policy_notes=("Tool is not in the policy inventory.",),
            redacted_arguments_preview=redacted_args,
            forbidden_fields=forbidden_fields,
            missing_required_fields=(),
            execution_allowed=False,
            dispatch_allowed=False,
            provider_schema_allowed=False,
            audit_written=False,
        )

    risk_tier = entry.primary_risk.value
    risk_rank = RISK_RANK[entry.primary_risk]

    # Step 3: Build combined reason codes and notes
    reason_codes: list[str] = []
    policy_notes: list[str] = []

    # Step 4: Check denylist first (highest priority)
    if entry.permanently_denied:
        reason_codes.append(WOULD_BLOCK_DENYLISTED)
        policy_notes.append("Tool is permanently denied by static policy.")
        return ToolDryRunResult(
            canonical_name=entry.canonical_name,
            exists=True,
            risk_tier=risk_tier,
            decision=DRY_RUN_DECISION_WOULD_BLOCK,
            reason_codes=_merge_reason_codes(reason_codes, arg_reason_codes),
            policy_notes=tuple(policy_notes),
            redacted_arguments_preview=redacted_args,
            forbidden_fields=forbidden_fields,
            missing_required_fields=(),
            execution_allowed=False,
            dispatch_allowed=False,
            provider_schema_allowed=False,
            audit_written=False,
        )

    # Step 5: Check STATIC_ALLOWLIST (must remain empty)
    if STATIC_ALLOWLIST:
        # If allowlist were populated, tools on it could be would_allow
        # But in this phase, STATIC_ALLOWLIST is always empty
        pass  # Defensive: allowlist check exists but does nothing

    # Step 6: Risk-tier based decisions
    if risk_rank >= 5:
        # R5: permanently blocked
        reason_codes.append(WOULD_BLOCK_R5_SYSTEM_RISK)
        policy_notes.append("High-risk system tool — dry-run blocked.")
        return ToolDryRunResult(
            canonical_name=entry.canonical_name,
            exists=True,
            risk_tier=risk_tier,
            decision=DRY_RUN_DECISION_WOULD_BLOCK,
            reason_codes=_merge_reason_codes(reason_codes, arg_reason_codes),
            policy_notes=tuple(policy_notes),
            redacted_arguments_preview=redacted_args,
            forbidden_fields=forbidden_fields,
            missing_required_fields=(),
            execution_allowed=False,
            dispatch_allowed=False,
            provider_schema_allowed=False,
            audit_written=False,
        )

    if risk_rank >= 4:
        # R4: blocked for execution risk
        reason_codes.append(WOULD_BLOCK_R4_EXECUTION_RISK)
        policy_notes.append("Process/execution tool — dry-run blocked.")
        return ToolDryRunResult(
            canonical_name=entry.canonical_name,
            exists=True,
            risk_tier=risk_tier,
            decision=DRY_RUN_DECISION_WOULD_BLOCK,
            reason_codes=_merge_reason_codes(reason_codes, arg_reason_codes),
            policy_notes=tuple(policy_notes),
            redacted_arguments_preview=redacted_args,
            forbidden_fields=forbidden_fields,
            missing_required_fields=(),
            execution_allowed=False,
            dispatch_allowed=False,
            provider_schema_allowed=False,
            audit_written=False,
        )

    # Step 7: R3 — controlled write → requires_review or would_redact
    if risk_rank == 3:
        reason_codes.append(REQUIRES_REVIEW_R3)
        policy_notes.append("Controlled-write tool — requires review.")
        # If arguments contain sensitive fields → would_redact
        if forbidden_fields or arg_reason_codes:
            decision = DRY_RUN_DECISION_WOULD_REDACT
            policy_notes.append("Arguments contain fields requiring redaction.")
        else:
            decision = DRY_RUN_DECISION_REQUIRES_REVIEW
        return ToolDryRunResult(
            canonical_name=entry.canonical_name,
            exists=True,
            risk_tier=risk_tier,
            decision=decision,
            reason_codes=_merge_reason_codes(reason_codes, arg_reason_codes),
            policy_notes=tuple(policy_notes),
            redacted_arguments_preview=redacted_args,
            forbidden_fields=forbidden_fields,
            missing_required_fields=(),
            execution_allowed=False,
            dispatch_allowed=False,
            provider_schema_allowed=False,
            audit_written=False,
        )

    # Step 8: R2 — read-only external network → requires_review
    if risk_rank == 2:
        reason_codes.append(REQUIRES_REVIEW_R2)
        policy_notes.append(
            "Read-only external network tool — requires review."
        )
        if entry.candidate_allowlisted:
            reason_codes.append(REQUIRES_REVIEW_CANDIDATE_ONLY)
            policy_notes.append("Tool is on candidate allowlist (advisory only).")
        return ToolDryRunResult(
            canonical_name=entry.canonical_name,
            exists=True,
            risk_tier=risk_tier,
            decision=DRY_RUN_DECISION_REQUIRES_REVIEW,
            reason_codes=_merge_reason_codes(reason_codes, arg_reason_codes),
            policy_notes=tuple(policy_notes),
            redacted_arguments_preview=redacted_args,
            forbidden_fields=forbidden_fields,
            missing_required_fields=(),
            execution_allowed=False,
            dispatch_allowed=False,
            provider_schema_allowed=False,
            audit_written=False,
        )

    # Step 9: R1 — read-only local query
    if risk_rank == 1:
        if entry.candidate_allowlisted:
            reason_codes.append(WOULD_ALLOW_STATIC_POLICY)
            reason_codes.append(DRY_RUN_ONLY_NO_EXECUTION)
            reason_codes.append(REQUIRES_REVIEW_CANDIDATE_ONLY)
            policy_notes.append(
                "Read-only local tool on candidate allowlist — "
                "would allow for dry-run simulation."
            )
            policy_notes.append(
                "Execution requires future STATIC_ALLOWLIST entry "
                "and separate phase approval."
            )
        else:
            reason_codes.append(WOULD_ALLOW_STATIC_POLICY)
            reason_codes.append(DRY_RUN_ONLY_NO_EXECUTION)
            policy_notes.append(
                "Read-only local tool — would allow for dry-run simulation."
            )
            policy_notes.append(
                "Execution requires future STATIC_ALLOWLIST entry "
                "and separate phase approval."
            )
        return ToolDryRunResult(
            canonical_name=entry.canonical_name,
            exists=True,
            risk_tier=risk_tier,
            decision=DRY_RUN_DECISION_WOULD_ALLOW,
            reason_codes=_merge_reason_codes(reason_codes, arg_reason_codes),
            policy_notes=tuple(policy_notes),
            redacted_arguments_preview=redacted_args,
            forbidden_fields=forbidden_fields,
            missing_required_fields=(),
            execution_allowed=False,
            dispatch_allowed=False,
            provider_schema_allowed=False,
            audit_written=False,
        )

    # Step 10: R0 — pure computation
    if risk_rank == 0:
        reason_codes.append(WOULD_ALLOW_STATIC_POLICY)
        reason_codes.append(DRY_RUN_ONLY_NO_EXECUTION)
        policy_notes.append(
            "Pure computation tool — would allow for dry-run simulation."
        )
        policy_notes.append(
            "Execution requires future STATIC_ALLOWLIST entry "
            "and separate phase approval."
        )
        if entry.candidate_allowlisted:
            reason_codes.append(REQUIRES_REVIEW_CANDIDATE_ONLY)
            policy_notes.append("Tool is on candidate allowlist (advisory only).")
        return ToolDryRunResult(
            canonical_name=entry.canonical_name,
            exists=True,
            risk_tier=risk_tier,
            decision=DRY_RUN_DECISION_WOULD_ALLOW,
            reason_codes=_merge_reason_codes(reason_codes, arg_reason_codes),
            policy_notes=tuple(policy_notes),
            redacted_arguments_preview=redacted_args,
            forbidden_fields=forbidden_fields,
            missing_required_fields=(),
            execution_allowed=False,
            dispatch_allowed=False,
            provider_schema_allowed=False,
            audit_written=False,
        )

    # Fallback (should not reach here)
    return ToolDryRunResult(
        canonical_name=entry.canonical_name,
        exists=True,
        risk_tier=risk_tier,
        decision=DRY_RUN_DECISION_WOULD_BLOCK,
        reason_codes=_merge_reason_codes(
            [WOULD_BLOCK_EXECUTION_DISABLED], arg_reason_codes
        ),
        policy_notes=("Unexpected risk tier — blocked.",),
        redacted_arguments_preview=redacted_args,
        forbidden_fields=forbidden_fields,
        missing_required_fields=(),
        execution_allowed=False,
        dispatch_allowed=False,
        provider_schema_allowed=False,
        audit_written=False,
    )


# ---------------------------------------------------------------------------
# 8. Catalog / summary
# ---------------------------------------------------------------------------


def list_tool_dry_run_policies() -> tuple[ToolDryRunResult, ...]:
    """Generate dry-run policy results for all 71 tools in inventory.

    Returns results sorted by canonical_name (stable alphabetical).

    Guarantees:
      - No tool handler calls
      - No provider calls
      - No runtime access
      - No audit storage
      - No filesystem/network access

    Returns:
        Tuple of ToolDryRunResult, one per tool, sorted by canonical_name.
    """
    results: list[ToolDryRunResult] = []
    for canonical_name in sorted(ALL_CANONICAL_TOOLS):
        result = dry_run_tool_policy(canonical_name)
        results.append(result)
    return tuple(results)


def compute_dry_run_policy_summary(
    results: tuple[ToolDryRunResult, ...] | None = None,
) -> ToolDryRunPolicySummary:
    """Compute aggregate summary from dry-run results.

    Args:
        results: Dry-run results to summarize. If None, generates for all tools.

    Returns:
        ToolDryRunPolicySummary with aggregate counts.
    """
    if results is None:
        results = list_tool_dry_run_policies()

    total = len(results)
    allow_count = 0
    blocked_count = 0
    review_count = 0
    redacted_count = 0

    for r in results:
        if r.decision == DRY_RUN_DECISION_WOULD_ALLOW:
            allow_count += 1
        elif r.decision == DRY_RUN_DECISION_WOULD_BLOCK:
            blocked_count += 1
        elif r.decision == DRY_RUN_DECISION_WOULD_REDACT:
            redacted_count += 1
        elif r.decision == DRY_RUN_DECISION_REQUIRES_REVIEW:
            review_count += 1

    return ToolDryRunPolicySummary(
        total_count=total,
        dry_run_allow_count=allow_count,
        blocked_count=blocked_count,
        review_count=review_count,
        redacted_count=redacted_count,
    )
