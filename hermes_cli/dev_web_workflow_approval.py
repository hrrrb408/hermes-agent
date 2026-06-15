"""Phase 3A Workflow Approval Gates for the Hermes Dev WebUI.

Human-approval gates for individual workflow steps. Each gate reuses the
Phase 2C-H1 file-backed confirmation store under a dedicated
``workflow_step_approval`` scope (separate from the ``write_execute`` /
``rollback_execute`` / ``provider_write_preview_confirm`` scopes) so a workflow
approval can never be replayed against a write or rollback execution.

Properties (frozen):
  - one explicit approval per step; an approval only authorizes the step it was
    issued for (step-id + execution-id + digest bound)
  - single-use: a consumed approval cannot be reused, even across process
    restarts (the underlying store persists ``usedAt``)
  - TTL-bounded (5 min default, 30 min hard cap)
  - the approval NEVER authorizes write execution or rollback execution — those
    keep their own scopes and confirmation flows
  - never persists the plain token, raw arguments, or file content (the
    underlying store hashes the secret + payload)
  - dev HERMES_HOME only; never ``~/.hermes``

Phase: 3A — Dev-only Agent Workflow MVP
Status: workflow approval gates implemented
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from hermes_cli.dev_web_confirmation_store import (
    BLOCKED_TOKEN_ALREADY_USED,
    BLOCKED_TOKEN_DIGEST_MISMATCH,
    BLOCKED_TOKEN_EXPIRED,
    BLOCKED_TOKEN_INVALID,
    BLOCKED_TOKEN_NOT_FOUND,
    BLOCKED_TOKEN_SCOPE_MISMATCH,
    DEFAULT_TTL_WORKFLOW_APPROVAL_SECONDS,
    SCOPE_WORKFLOW_STEP_APPROVAL,
    create_confirmation_token,
    mark_confirmation_token_used,
    verify_confirmation_token,
)
from hermes_cli.dev_web_workflow_schema import (
    BLOCKED_APPROVAL_ALREADY_USED,
    BLOCKED_APPROVAL_DIGEST_MISMATCH,
    BLOCKED_APPROVAL_EXPIRED,
    BLOCKED_APPROVAL_REQUIRED,
    BLOCKED_APPROVAL_SCOPE_MISMATCH,
    BLOCKED_APPROVAL_STEP_MISMATCH,
    WORKFLOW_EXECUTION_ID_PREFIX,
    WorkflowApprovalGate,
)


# ---------------------------------------------------------------------------
# 1. Step digest
# ---------------------------------------------------------------------------


def compute_step_digest(
    *,
    workflow_execution_id: str,
    step_id: str,
    step_type: str,
    step_input: Mapping[str, Any] | None,
) -> str:
    """Compute a stable SHA-256 digest binding an approval to one step.

    The digest covers the execution id, step id, step type, and the sanitized
    step input — so an approval issued for one step/input cannot satisfy a
    different step or a step whose input changed after approval.
    """
    payload = {
        "execution": workflow_execution_id,
        "step": step_id,
        "type": step_type,
        "input": dict(step_input) if step_input else {},
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 2. Issue
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WorkflowApprovalIssueResult:
    issued: bool
    approval: WorkflowApprovalGate | None
    raw_token: str | None
    blocked_reason: str | None
    error_code: str | None


def issue_step_approval(
    *,
    workflow_execution_id: str,
    step_id: str,
    step_type: str,
    step_input: Mapping[str, Any] | None,
    hermes_home: str | None = None,
    ttl_seconds: int = DEFAULT_TTL_WORKFLOW_APPROVAL_SECONDS,
) -> WorkflowApprovalIssueResult:
    """Issue a single-use approval token bound to one workflow step."""
    if not workflow_execution_id.startswith(WORKFLOW_EXECUTION_ID_PREFIX):
        return WorkflowApprovalIssueResult(
            False, None, None, BLOCKED_APPROVAL_STEP_MISMATCH, "workflow_approval_invalid_execution"
        )
    digest = compute_step_digest(
        workflow_execution_id=workflow_execution_id,
        step_id=step_id,
        step_type=step_type,
        step_input=step_input,
    )
    payload = {
        "workflowExecutionId": workflow_execution_id,
        "stepId": step_id,
        "stepType": step_type,
        "stepDigest": digest,
    }
    issue = create_confirmation_token(
        payload,
        scope=SCOPE_WORKFLOW_STEP_APPROVAL,
        argument_digest=digest,
        tool_id=None,
        operation="workflow_step_approval",
        ttl_seconds=ttl_seconds,
        metadata={"workflowExecutionId": workflow_execution_id, "stepId": step_id},
        hermes_home=hermes_home,
    )
    if issue is None:
        return WorkflowApprovalIssueResult(
            False, None, None, BLOCKED_STORE_REASON, "workflow_approval_issue_failed"
        )
    # The approval id IS the underlying confirmation-token id (cft_…) — the
    # workflow approval is a confirmation token under a dedicated scope, so we
    # surface its real id rather than inventing a second prefix.
    approval_id = issue.tokenId
    gate = WorkflowApprovalGate(
        approval_id=approval_id,
        step_id=step_id,
        workflow_execution_id=workflow_execution_id,
        step_digest=digest,
        issued_at=_now_iso(),
        expires_at=issue.expiresAt,
        used_at=None,
    )
    return WorkflowApprovalIssueResult(True, gate, issue.token, None, None)


# ---------------------------------------------------------------------------
# 3. Verify + consume
# ---------------------------------------------------------------------------


# Store-unavailable sentinel mapped to the workflow approval-required reason.
BLOCKED_STORE_REASON = BLOCKED_APPROVAL_REQUIRED


@dataclass(frozen=True, slots=True)
class WorkflowApprovalVerifyResult:
    verified: bool
    approval_id: str | None
    blocked_reason: str | None


def verify_step_approval(
    *,
    raw_token: str | None,
    workflow_execution_id: str,
    step_id: str,
    step_type: str,
    step_input: Mapping[str, Any] | None,
    hermes_home: str | None = None,
) -> WorkflowApprovalVerifyResult:
    """Verify an approval token against the expected step binding.

    Maps the underlying confirmation-store blocked reasons to the workflow
    approval blocked reasons. Does NOT consume the token.
    """
    if not raw_token:
        return WorkflowApprovalVerifyResult(False, None, BLOCKED_APPROVAL_REQUIRED)

    expected_digest = compute_step_digest(
        workflow_execution_id=workflow_execution_id,
        step_id=step_id,
        step_type=step_type,
        step_input=step_input,
    )
    result = verify_confirmation_token(
        raw_token,
        expected_scope=SCOPE_WORKFLOW_STEP_APPROVAL,
        expected_digest=expected_digest,
        hermes_home=hermes_home,
    )
    if result.verified and result.record is not None:
        # Confirm the token's stored metadata binds it to THIS step + execution.
        meta = result.record.metadata or {}
        if (
            str(meta.get("workflowExecutionId", "")) != workflow_execution_id
            or str(meta.get("stepId", "")) != step_id
        ):
            return WorkflowApprovalVerifyResult(False, None, BLOCKED_APPROVAL_STEP_MISMATCH)
        return WorkflowApprovalVerifyResult(
            True, result.record.tokenId, None
        )

    reason = _map_token_blocked_reason(result.blocked_reason)
    return WorkflowApprovalVerifyResult(False, None, reason)


def consume_step_approval(
    *,
    raw_token: str | None,
    workflow_execution_id: str,
    step_id: str,
    step_type: str,
    step_input: Mapping[str, Any] | None,
    hermes_home: str | None = None,
) -> WorkflowApprovalVerifyResult:
    """Verify AND mark-used an approval token (single-use consumption)."""
    verify = verify_step_approval(
        raw_token=raw_token,
        workflow_execution_id=workflow_execution_id,
        step_id=step_id,
        step_type=step_type,
        step_input=step_input,
        hermes_home=hermes_home,
    )
    if not verify.verified:
        return verify
    # Mark the underlying token used so it cannot be replayed.
    token_id = _token_id_from_raw(raw_token)
    if token_id is not None:
        mark_confirmation_token_used(token_id, hermes_home=hermes_home)
    return verify


# ---------------------------------------------------------------------------
# 4. Helpers
# ---------------------------------------------------------------------------


def _map_token_blocked_reason(reason: str | None) -> str:
    mapping = {
        BLOCKED_TOKEN_NOT_FOUND: BLOCKED_APPROVAL_REQUIRED,
        BLOCKED_TOKEN_INVALID: BLOCKED_APPROVAL_REQUIRED,
        BLOCKED_TOKEN_EXPIRED: BLOCKED_APPROVAL_EXPIRED,
        BLOCKED_TOKEN_ALREADY_USED: BLOCKED_APPROVAL_ALREADY_USED,
        BLOCKED_TOKEN_SCOPE_MISMATCH: BLOCKED_APPROVAL_SCOPE_MISMATCH,
        BLOCKED_TOKEN_DIGEST_MISMATCH: BLOCKED_APPROVAL_DIGEST_MISMATCH,
    }
    return mapping.get(reason or "", BLOCKED_APPROVAL_REQUIRED)


def _token_id_from_raw(raw_token: str | None) -> str | None:
    if not isinstance(raw_token, str) or "." not in raw_token:
        return None
    token_id, _, _secret = raw_token.rpartition(".")
    return token_id or None


def _now_iso() -> str:
    """Current UTC ISO-8601 timestamp (issued-at stamp)."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "compute_step_digest",
    "issue_step_approval",
    "verify_step_approval",
    "consume_step_approval",
    "WorkflowApprovalIssueResult",
    "WorkflowApprovalVerifyResult",
]
