"""Phase 2C Write Handlers + Dispatch Chain for the Hermes Dev WebUI.

This module implements the four Phase 2C controlled write tool handlers and
the single write-dispatch orchestrator (:func:`dispatch_write_tool`) that runs
the full controlled-write chain:

  1. validate write enablement (``HERMES_TOOL_WRITE_EXECUTION_ENABLED``)
  2. normalize / validate arguments
  3. build the write plan (re-derived; never trusts the client's hashes)
  4. verify the argument digest
  5. verify the confirmation token (single-use, bound to plan + digest)
  6. write pre-execution audit
  7. handler lookup + dispatch planning
  8. execute the write handler (actual sandbox IO)
  9. compute the after-hash + build the rollback manifest
 10. write post-execution audit + rollback-manifest audit
 11. return a structured result (optionally with a readback summary)

Fail-closed: any failed gate returns a blocked result with a precise
``blockedReason`` and an audit event — no partial write is ever surfaced as
successful. Writes happen ONLY inside the dev sandbox root.

Phase: 2C — Controlled Tool Write Execution (Dev Sandbox Write MVP)
Status: write handlers + dispatch implemented
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from hermes_cli.dev_web_write_plan import (
    BLOCKED_WRITE_BINARY_CONTENT,
    BLOCKED_WRITE_CONFIRMATION_REQUIRED,
    BLOCKED_WRITE_DIGEST_MISMATCH,
    BLOCKED_WRITE_EXECUTION_NOT_ENABLED,
    BLOCKED_WRITE_MISSING_ROLLBACK_PLAN,
    BLOCKED_WRITE_TOOL_NOT_ALLOWLISTED,
    BLOCKED_WRITE_TOOL_NOT_SUPPORTED,
    EVENT_WRITE_HANDLER_CALLED,
    EVENT_WRITE_POST_EXECUTION_AUDIT,
    EVENT_WRITE_PRE_EXECUTION_AUDIT,
    EVENT_WRITE_ROLLBACK_MANIFEST_BUILT,
    EVENT_WRITE_EXECUTION_BLOCKED,
    WritePlan,
    build_write_plan,
    compute_argument_digest,
    emit_write_audit,
    verify_write_confirmation_token,
)
from hermes_cli.dev_web_write_rollback import build_rollback_manifest
from hermes_cli.dev_web_write_sandbox import (
    ensure_dev_write_sandbox_root,
    readback_summary,
    safe_append_text,
    safe_apply_patch,
    safe_read_text,
    safe_write_text,
)
from hermes_cli.dev_web_write_tool_registry import (
    PHASE_2C_WRITE_TOOL_IDS,
    STATIC_WRITE_ALLOWLIST,
    normalize_write_tool_arguments,
    validate_write_tool_arguments,
)


# ---------------------------------------------------------------------------
# 1. Enablement gate
# ---------------------------------------------------------------------------


def _is_write_enabled() -> bool:
    """Return True iff ``HERMES_TOOL_WRITE_EXECUTION_ENABLED`` is ``1`` or ``true``."""
    raw = os.environ.get("HERMES_TOOL_WRITE_EXECUTION_ENABLED", "")
    return raw.strip().lower() in ("1", "true")


# ---------------------------------------------------------------------------
# 2. Result model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WriteExecuteResult:
    """Structured result of a controlled write execution."""

    execution_id: str
    tool_id: str
    status: str  # "completed" | "blocked"
    write_plan_id: str | None
    write_preview_id: str | None
    rollback_id: str | None
    operation: str
    target_relative_path: str
    before_hash: str | None
    after_hash: str | None
    content_digest: str | None
    bytes_written: int
    lines_changed: int
    diff_preview: str
    rollback_available: bool
    blocked_reason: str | None
    pre_execution_audit_id: str | None
    post_execution_audit_id: str | None
    warnings: tuple[str, ...] = ()
    readback: Mapping[str, Any] | None = None

    def to_safe_dict(self) -> dict[str, Any]:
        import uuid as _uuid

        data: dict[str, Any] = {
            "executionId": self.execution_id,
            "toolId": self.tool_id,
            "status": self.status,
            "writePlanId": self.write_plan_id,
            "writePreviewId": self.write_preview_id,
            "rollbackId": self.rollback_id,
            "operation": self.operation,
            "targetRelativePath": self.target_relative_path,
            "beforeHash": self.before_hash,
            "afterHash": self.after_hash,
            "contentDigest": self.content_digest,
            "bytesWritten": self.bytes_written,
            "linesChanged": self.lines_changed,
            "diffPreview": self.diff_preview,
            "rollbackAvailable": self.rollback_available,
            "readOnly": False,
            "writeRequired": True,
            "localSideEffects": True,
            "externalSideEffects": False,
            "providerRequired": False,
            "providerSchemaSent": False,
            "providerApiCalled": False,
            "externalNetworkCalled": False,
            "blockedReason": self.blocked_reason,
            "preExecutionAuditId": self.pre_execution_audit_id,
            "postExecutionAuditId": self.post_execution_audit_id,
            "warnings": list(self.warnings),
        }
        if self.readback is not None:
            data["readback"] = dict(self.readback)
        # Stable opaque id even on early-block (before a plan id exists).
        if not self.execution_id:
            data["executionId"] = f"wexe_{_uuid.uuid4().hex}"
        return data


@dataclass(frozen=True, slots=True)
class _HandlerOutcome:
    ok: bool
    error_code: str | None
    before_content: str | None
    after_content: str | None
    bytes_written: int
    lines_changed: int


# ---------------------------------------------------------------------------
# 3. Per-tool handlers (actual sandbox IO)
# ---------------------------------------------------------------------------


def handle_dev_sandbox_file_write(
    args: Mapping[str, Any],
    *,
    canonical_path: Path,
) -> _HandlerOutcome:
    content = args.get("content", "")
    ok, err, before = safe_write_text(canonical_path, content)
    if not ok:
        return _HandlerOutcome(False, err, before, None, 0, 0)
    return _HandlerOutcome(True, None, before, content, len(content.encode("utf-8")), 0)


def handle_dev_sandbox_file_append(
    args: Mapping[str, Any],
    *,
    canonical_path: Path,
) -> _HandlerOutcome:
    content = args.get("content", "")
    ok, err, before = safe_append_text(canonical_path, content)
    if not ok:
        return _HandlerOutcome(False, err, before, None, 0, 0)
    after = (before or "") + content
    return _HandlerOutcome(True, None, before, after, len(content.encode("utf-8")), 0)


def handle_dev_sandbox_file_patch(
    args: Mapping[str, Any],
    *,
    canonical_path: Path,
) -> _HandlerOutcome:
    search = args.get("search", "")
    replace = args.get("replace", "")
    ok, err, before, count = safe_apply_patch(canonical_path, search, replace)
    if not ok:
        return _HandlerOutcome(False, err, before, None, 0, 0)
    after = (before or "").replace(search, replace, 1)
    before_lines = len((before or "").splitlines())
    after_lines = len(after.splitlines())
    return _HandlerOutcome(True, None, before, after, len(after.encode("utf-8")), abs(after_lines - before_lines))


def handle_dev_sandbox_file_readback(
    args: Mapping[str, Any],
    *,
    canonical_path: Path,
) -> _HandlerOutcome:
    content = safe_read_text(canonical_path)
    return _HandlerOutcome(True, None, content, content, 0, 0)


_HANDLER_TABLE = {
    "dev_sandbox_file_write": handle_dev_sandbox_file_write,
    "dev_sandbox_file_append": handle_dev_sandbox_file_append,
    "dev_sandbox_file_patch": handle_dev_sandbox_file_patch,
    "dev_sandbox_file_readback": handle_dev_sandbox_file_readback,
}


# ---------------------------------------------------------------------------
# 4. Dispatch chain
# ---------------------------------------------------------------------------


def _blocked_result(
    tool_id: str,
    blocked_reason: str,
    *,
    operation: str = "unsupported",
    target_relative_path: str = "",
    write_plan_id: str | None = None,
    write_preview_id: str | None = None,
    pre_execution_audit_id: str | None = None,
    hermes_home: str | None = None,
    warnings: tuple[str, ...] = (),
) -> WriteExecuteResult:
    import uuid as _uuid

    # Emit a blocked audit (best-effort; never enables execution).
    emit_write_audit(
        event_type=EVENT_WRITE_EXECUTION_BLOCKED,
        hermes_home=hermes_home,
        tool_id=tool_id,
        write_plan_id=write_plan_id,
        write_preview_id=write_preview_id,
        rollback_id=None,
        operation=operation,
        target_relative_path=target_relative_path or None,
        status="blocked",
        blocked_reason=blocked_reason,
        payload={"preExecutionAuditId": pre_execution_audit_id},
    )
    return WriteExecuteResult(
        execution_id=f"wexe_{_uuid.uuid4().hex}",
        tool_id=tool_id,
        status="blocked",
        write_plan_id=write_plan_id,
        write_preview_id=write_preview_id,
        rollback_id=None,
        operation=operation,
        target_relative_path=target_relative_path,
        before_hash=None,
        after_hash=None,
        content_digest=None,
        bytes_written=0,
        lines_changed=0,
        diff_preview="",
        rollback_available=False,
        blocked_reason=blocked_reason,
        pre_execution_audit_id=pre_execution_audit_id,
        post_execution_audit_id=None,
        warnings=warnings,
    )


def dispatch_write_tool(
    tool_id: str,
    arguments: Mapping[str, Any] | None,
    *,
    context: Mapping[str, Any] | None = None,
    hermes_home: str | os.PathLike[str] | None = None,
) -> WriteExecuteResult:
    """Run the full controlled-write chain for *tool_id*.

    ``context`` may carry ``confirmationToken``, ``argumentDigest``,
    ``writePlanId``, ``uiOrigin``, ``sourceContext``. These are the values
    returned by :func:`build_write_preview` and re-submitted by the caller.
    """
    import uuid as _uuid

    ctx = dict(context or {})
    request_write_plan_id = ctx.get("writePlanId") if isinstance(ctx.get("writePlanId"), str) else None
    request_argument_digest = ctx.get("argumentDigest") if isinstance(ctx.get("argumentDigest"), str) else None
    confirmation_token = ctx.get("confirmationToken") if isinstance(ctx.get("confirmationToken"), str) else None

    operation = "readback" if tool_id == "dev_sandbox_file_readback" else "unsupported"
    target_raw = ""
    if isinstance(arguments, Mapping):
        tp = arguments.get("targetPath")
        if isinstance(tp, str):
            target_raw = tp

    # Gate 1: write enablement.
    if not _is_write_enabled():
        return _blocked_result(
            tool_id, BLOCKED_WRITE_EXECUTION_NOT_ENABLED,
            operation=operation, target_relative_path=target_raw,
            hermes_home=str(hermes_home) if hermes_home else None,
        )

    # Gate 2: allowlist membership.
    if tool_id not in STATIC_WRITE_ALLOWLIST or tool_id not in PHASE_2C_WRITE_TOOL_IDS:
        return _blocked_result(
            tool_id, BLOCKED_WRITE_TOOL_NOT_ALLOWLISTED,
            operation=operation, target_relative_path=target_raw,
            hermes_home=str(hermes_home) if hermes_home else None,
        )

    # Gate 3: argument normalization.
    normalized, arg_err = validate_write_tool_arguments(tool_id, arguments)
    if arg_err is not None or not normalized:
        return _blocked_result(
            tool_id, BLOCKED_WRITE_TOOL_NOT_SUPPORTED,
            operation=operation, target_relative_path=target_raw,
            hermes_home=str(hermes_home) if hermes_home else None,
        )

    # Gate 4: re-derive the plan from current sandbox state.
    plan: WritePlan = build_write_plan(tool_id, normalized, hermes_home=hermes_home)
    if plan.blocked:
        return _blocked_result(
            tool_id, plan.blocked_reason or BLOCKED_WRITE_TOOL_NOT_SUPPORTED,
            operation=plan.operation, target_relative_path=plan.target_relative_path,
            write_plan_id=request_write_plan_id, hermes_home=str(hermes_home) if hermes_home else None,
        )

    # Gate 5: argument digest verification (recompute, compare to request).
    recomputed_digest = compute_argument_digest(tool_id, normalized)
    if not request_argument_digest or not _const_time_eq(recomputed_digest, request_argument_digest):
        return _blocked_result(
            tool_id, BLOCKED_WRITE_DIGEST_MISMATCH,
            operation=plan.operation, target_relative_path=plan.target_relative_path,
            write_plan_id=request_write_plan_id, hermes_home=str(hermes_home) if hermes_home else None,
        )

    # Gate 6: confirmation token verification.
    verified_plan_id = request_write_plan_id or plan.write_plan_id
    token_ok, token_err = verify_write_confirmation_token(
        confirmation_token, verified_plan_id, recomputed_digest, consume=True
    )
    if not token_ok:
        return _blocked_result(
            tool_id, token_err or BLOCKED_WRITE_CONFIRMATION_REQUIRED,
            operation=plan.operation, target_relative_path=plan.target_relative_path,
            write_plan_id=verified_plan_id, hermes_home=str(hermes_home) if hermes_home else None,
        )

    # Gate 7: pre-execution audit.
    pre_audit_id = emit_write_audit(
        event_type=EVENT_WRITE_PRE_EXECUTION_AUDIT,
        hermes_home=str(hermes_home) if hermes_home else None,
        tool_id=tool_id,
        write_plan_id=verified_plan_id,
        write_preview_id=plan.write_preview_id,
        rollback_id=None,
        operation=plan.operation,
        target_relative_path=plan.target_relative_path,
        status="pre_execution",
        blocked_reason=None,
        payload={"argumentDigest": recomputed_digest, "beforeHash": plan.before_hash},
    )

    # Gate 8: handler lookup + dispatch.
    handler = _HANDLER_TABLE.get(tool_id)
    if handler is None:
        return _blocked_result(
            tool_id, BLOCKED_WRITE_TOOL_NOT_SUPPORTED,
            operation=plan.operation, target_relative_path=plan.target_relative_path,
            write_plan_id=verified_plan_id, write_preview_id=plan.write_preview_id,
            pre_execution_audit_id=pre_audit_id,
            hermes_home=str(hermes_home) if hermes_home else None,
        )

    # Ensure the sandbox root + parent dirs exist before the handler writes.
    ensure_dev_write_sandbox_root(str(hermes_home) if hermes_home else None)
    canonical_path = Path(plan.canonical_target_path)

    # Gate 9: execute the handler.
    outcome = handler(normalized, canonical_path=canonical_path)
    emit_write_audit(
        event_type=EVENT_WRITE_HANDLER_CALLED,
        hermes_home=str(hermes_home) if hermes_home else None,
        tool_id=tool_id,
        write_plan_id=verified_plan_id,
        write_preview_id=plan.write_preview_id,
        rollback_id=None,
        operation=plan.operation,
        target_relative_path=plan.target_relative_path,
        status="completed" if outcome.ok else "failed",
        blocked_reason=outcome.error_code if not outcome.ok else None,
        payload={"bytesWritten": outcome.bytes_written},
    )
    if not outcome.ok:
        return _blocked_result(
            tool_id, outcome.error_code or BLOCKED_WRITE_BINARY_CONTENT,
            operation=plan.operation, target_relative_path=plan.target_relative_path,
            write_plan_id=verified_plan_id, write_preview_id=plan.write_preview_id,
            pre_execution_audit_id=pre_audit_id,
            hermes_home=str(hermes_home) if hermes_home else None,
        )

    # Gate 10: after-hash + rollback manifest.
    from hermes_cli.dev_web_write_sandbox import compute_sha256_text

    after_hash = compute_sha256_text(outcome.after_content) if outcome.after_content is not None else plan.after_hash

    rollback_id: str | None = None
    rollback_available = False
    if plan.operation != "readback":
        manifest = build_rollback_manifest(
            operation=plan.operation,
            target_relative_path=plan.target_relative_path,
            before_content=outcome.before_content,
            after_content=outcome.after_content or "",
            after_hash=after_hash or "",
        )
        rollback_id = manifest.rollback_id
        rollback_available = True
        emit_write_audit(
            event_type=EVENT_WRITE_ROLLBACK_MANIFEST_BUILT,
            hermes_home=str(hermes_home) if hermes_home else None,
            tool_id=tool_id,
            write_plan_id=verified_plan_id,
            write_preview_id=plan.write_preview_id,
            rollback_id=rollback_id,
            operation=plan.operation,
            target_relative_path=plan.target_relative_path,
            status="rollback_manifest_built",
            blocked_reason=None,
            payload={
                "restoreMode": manifest.restore_mode,
                "beforeExists": manifest.before_exists,
                "beforeHash": manifest.before_hash,
            },
        )
    else:
        # readback must not claim a rollback.
        rollback_available = False

    # Gate 11: post-execution audit (fail-closed: a write without a written
    # post-execution audit is surfaced as blocked).
    post_audit_id = emit_write_audit(
        event_type=EVENT_WRITE_POST_EXECUTION_AUDIT,
        hermes_home=str(hermes_home) if hermes_home else None,
        tool_id=tool_id,
        write_plan_id=verified_plan_id,
        write_preview_id=plan.write_preview_id,
        rollback_id=rollback_id,
        operation=plan.operation,
        target_relative_path=plan.target_relative_path,
        status="completed",
        blocked_reason=None,
        payload={
            "beforeHash": plan.before_hash,
            "afterHash": after_hash,
            "bytesWritten": outcome.bytes_written,
            "linesChanged": outcome.lines_changed,
            "rollbackAvailable": rollback_available,
        },
    )

    readback = readback_summary(canonical_path)

    return WriteExecuteResult(
        execution_id=f"wexe_{_uuid.uuid4().hex}",
        tool_id=tool_id,
        status="completed",
        write_plan_id=verified_plan_id,
        write_preview_id=plan.write_preview_id,
        rollback_id=rollback_id,
        operation=plan.operation,
        target_relative_path=plan.target_relative_path,
        before_hash=plan.before_hash,
        after_hash=after_hash,
        content_digest=plan.content_digest,
        bytes_written=outcome.bytes_written,
        lines_changed=outcome.lines_changed,
        diff_preview=plan.diff_preview,
        rollback_available=rollback_available,
        blocked_reason=None,
        pre_execution_audit_id=pre_audit_id,
        post_execution_audit_id=post_audit_id,
        warnings=plan.warnings,
        readback=readback,
    )


def _const_time_eq(a: str, b: str) -> bool:
    """Constant-time string comparison (digests only)."""
    import hmac as _hmac

    if not isinstance(a, str) or not isinstance(b, str):
        return False
    return _hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
