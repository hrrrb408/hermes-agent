"""Phase 2C Write Plan / Preview / Audit / Confirmation for the Hermes Dev WebUI.

This module owns the Phase 2C write lifecycle machinery that is NOT the actual
file IO (that lives in ``dev_web_write_sandbox.py``) and NOT the per-tool
dispatch orchestration (that lives in ``dev_web_write_handlers.py``):

  - :class:`WritePlan` — the dry-run plan (before/after hashes, diff preview,
    rollback preview, blocked reason). Building a plan NEVER writes a file.
  - :func:`build_write_preview` — the public preview envelope, which issues a
    one-time confirmation token bound to the plan.
  - the write audit writer (events written to
    ``$HERMES_HOME/gateway/dev/audit/tool-write-audit.jsonl``).
  - the write confirmation token (stateless binding + in-memory single-use set;
    file-backed TTL persistence is deferred to Phase 2C-H1 / Phase 2D).
  - :func:`build_provider_write_preview` — the provider write preview
    (preview-only; never auto-executes).

Architecture constraints:
  - stdlib only (no third-party imports)
  - audit file written only under the dev HERMES_HOME dev audit dir
  - never accesses ~/.hermes, never accesses production state.db
  - never stores API keys, raw tokens, full tokenHash, raw arguments, secrets,
    callable reprs, or function reprs
  - every audit payload is defensively re-redacted before serialization
  - write failure never enables execution

Phase: 2C — Controlled Tool Write Execution (Dev Sandbox Write MVP)
Status: write plan / preview / audit / confirmation implemented
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from hermes_cli.dev_web_write_tool_registry import (
    PHASE_2C_WRITE_TOOL_IDS,
    STATIC_WRITE_ALLOWLIST,
    get_write_tool_definition,
    normalize_write_tool_arguments,
)


# ---------------------------------------------------------------------------
# 1. Operation mapping
# ---------------------------------------------------------------------------

_TOOL_OPERATION: Mapping[str, str] = {
    "dev_sandbox_file_write": "create_or_replace",
    "dev_sandbox_file_append": "append",
    "dev_sandbox_file_patch": "patch",
    "dev_sandbox_file_readback": "readback",
}

_WRITE_RISK_TIER = "dev_sandbox_write"
_SANDBOX_ROOT_LABEL = "dev tool-write-sandbox (under dev HERMES_HOME)"


# ---------------------------------------------------------------------------
# 2. Blocked reason codes
# ---------------------------------------------------------------------------

BLOCKED_WRITE_EXECUTION_NOT_ENABLED = "blocked_write_execution_not_enabled"
BLOCKED_WRITE_TOOL_NOT_ALLOWLISTED = "blocked_write_tool_not_allowlisted"
BLOCKED_WRITE_TOOL_NOT_SUPPORTED = "blocked_write_tool_not_supported"
BLOCKED_WRITE_PATH_TRAVERSAL = "blocked_write_path_traversal"
BLOCKED_WRITE_ABSOLUTE_PATH = "blocked_write_absolute_path"
BLOCKED_WRITE_SYMLINK_ESCAPE = "blocked_write_symlink_escape"
BLOCKED_WRITE_FORBIDDEN_PATH = "blocked_write_forbidden_path"
BLOCKED_WRITE_FILE_TOO_LARGE = "blocked_write_file_too_large"
BLOCKED_WRITE_CONTENT_TOO_LARGE = "blocked_write_content_too_large"
BLOCKED_WRITE_BINARY_CONTENT = "blocked_write_binary_content"
BLOCKED_WRITE_MISSING_ROLLBACK_PLAN = "blocked_write_missing_rollback_plan"
BLOCKED_WRITE_DIGEST_MISMATCH = "blocked_write_digest_mismatch"
BLOCKED_WRITE_CONFIRMATION_REQUIRED = "blocked_write_confirmation_required"
BLOCKED_WRITE_PROVIDER_AUTO_EXECUTE_DENIED = "blocked_write_provider_auto_execute_denied"
BLOCKED_WRITE_PATCH_NO_UNIQUE_MATCH = "blocked_write_patch_no_unique_match"

# Sandbox error-code → write blocked-reason mapping (keeps the public vocabulary
# stable while reusing the sandbox validator outputs).
_SANDBOX_ERR_TO_BLOCKED: Mapping[str, str] = {
    "blocked_write_path_traversal": BLOCKED_WRITE_PATH_TRAVERSAL,
    "blocked_write_absolute_path": BLOCKED_WRITE_ABSOLUTE_PATH,
    "blocked_write_symlink_escape": BLOCKED_WRITE_SYMLINK_ESCAPE,
    "blocked_write_forbidden_path": BLOCKED_WRITE_FORBIDDEN_PATH,
    "blocked_write_file_type": BLOCKED_WRITE_FORBIDDEN_PATH,
    "blocked_write_content_too_large": BLOCKED_WRITE_CONTENT_TOO_LARGE,
    "blocked_write_file_too_large": BLOCKED_WRITE_FILE_TOO_LARGE,
    "blocked_write_binary_content": BLOCKED_WRITE_BINARY_CONTENT,
    "blocked_write_filename_too_long": BLOCKED_WRITE_PATH_TRAVERSAL,
    "blocked_write_path_too_deep": BLOCKED_WRITE_PATH_TRAVERSAL,
    "blocked_write_empty_path": BLOCKED_WRITE_TOOL_NOT_SUPPORTED,
    "write_dev_home_production": BLOCKED_WRITE_FORBIDDEN_PATH,
    "write_dev_home_unset": BLOCKED_WRITE_TOOL_NOT_SUPPORTED,
}


# ---------------------------------------------------------------------------
# 3. Argument digest
# ---------------------------------------------------------------------------


def compute_argument_digest(tool_id: str, normalized_args: Mapping[str, Any]) -> str:
    """Return a stable SHA-256 digest binding *tool_id* to its normalized args."""
    canonical = json.dumps(
        {"tool": tool_id, "args": dict(normalized_args)},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 4. Write plan
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WritePlan:
    """Immutable dry-run plan for one controlled write."""

    write_plan_id: str
    write_preview_id: str
    tool_id: str
    operation: str
    sandbox_root_label: str
    target_relative_path: str
    canonical_target_path: str
    before_exists: bool
    before_hash: str | None
    after_hash: str | None
    content_digest: str | None
    diff_preview: str
    risk_tier: str
    requires_confirmation: bool
    requires_write_enablement: bool
    rollback_preview: str
    blocked: bool
    blocked_reason: str | None
    warnings: tuple[str, ...]
    argument_digest: str
    normalized_args: Mapping[str, Any] = field(default_factory=dict)

    def to_safe_dict(self) -> dict[str, Any]:
        """Public-safe dict. Never exposes raw arguments or the sandbox path."""
        return {
            "writePlanId": self.write_plan_id,
            "writePreviewId": self.write_preview_id,
            "toolId": self.tool_id,
            "operation": self.operation,
            "sandboxRootLabel": self.sandbox_root_label,
            "targetRelativePath": self.target_relative_path,
            "beforeExists": self.before_exists,
            "beforeHash": self.before_hash,
            "afterHash": self.after_hash,
            "contentDigest": self.content_digest,
            "diffPreview": self.diff_preview,
            "riskTier": self.risk_tier,
            "readOnly": False,
            "writeRequired": True,
            "localSideEffects": True,
            "externalSideEffects": False,
            "providerRequired": False,
            "requiresConfirmation": self.requires_confirmation,
            "requiresWriteEnablement": self.requires_write_enablement,
            "requiresRollbackPlan": True,
            "rollbackPreview": self.rollback_preview,
            "blocked": self.blocked,
            "blockedReason": self.blocked_reason,
            "warnings": list(self.warnings),
            "argumentDigest": self.argument_digest,
        }


def _blocked_plan(
    tool_id: str,
    target_relative_path: str,
    operation: str,
    blocked_reason: str,
    *,
    argument_digest: str = "",
    warnings: tuple[str, ...] = (),
) -> WritePlan:
    return WritePlan(
        write_plan_id=f"wpln_{uuid.uuid4().hex}",
        write_preview_id=f"wprv_{uuid.uuid4().hex}",
        tool_id=tool_id,
        operation=operation,
        sandbox_root_label=_SANDBOX_ROOT_LABEL,
        target_relative_path=target_relative_path,
        canonical_target_path="",
        before_exists=False,
        before_hash=None,
        after_hash=None,
        content_digest=None,
        diff_preview="",
        risk_tier=_WRITE_RISK_TIER,
        requires_confirmation=True,
        requires_write_enablement=True,
        rollback_preview="",
        blocked=True,
        blocked_reason=blocked_reason,
        warnings=warnings,
        argument_digest=argument_digest,
    )


def build_write_plan(
    tool_id: str,
    normalized_args: Mapping[str, Any] | None,
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> WritePlan:
    """Build a dry-run plan for *tool_id*. NEVER writes a file.

    Validates the tool, the arguments, and the sandbox target; computes
    before/after hashes and a diff preview; produces a rollback preview. On any
    validation failure the plan is returned with ``blocked=True`` and a precise
    ``blocked_reason``.
    """
    from hermes_cli.dev_web_write_sandbox import (
        build_diff_preview,
        compute_sha256_text,
        safe_read_text,
        validate_sandbox_target_path,
        validate_file_size_limits,
    )
    from hermes_cli.dev_web_write_rollback import (
        RESTORE_MODE_NONE,
        build_rollback_manifest,
    )

    operation = _TOOL_OPERATION.get(tool_id, "unsupported")
    target_raw = ""
    if isinstance(normalized_args, Mapping):
        tp = normalized_args.get("targetPath")
        if isinstance(tp, str):
            target_raw = tp

    if tool_id not in PHASE_2C_WRITE_TOOL_IDS:
        return _blocked_plan(tool_id, target_raw, operation, BLOCKED_WRITE_TOOL_NOT_SUPPORTED)
    if tool_id not in STATIC_WRITE_ALLOWLIST:
        return _blocked_plan(tool_id, target_raw, operation, BLOCKED_WRITE_TOOL_NOT_ALLOWLISTED)

    # Normalize / validate arguments.
    from hermes_cli.dev_web_write_tool_registry import validate_write_tool_arguments

    normalized, arg_err = validate_write_tool_arguments(tool_id, normalized_args)
    if arg_err is not None or not normalized:
        # Map a registry binary rejection to the precise write reason.
        from hermes_cli.dev_web_write_tool_registry import _ARG_ERROR_BINARY_CONTENT

        reason = (
            BLOCKED_WRITE_BINARY_CONTENT
            if arg_err == _ARG_ERROR_BINARY_CONTENT
            else BLOCKED_WRITE_TOOL_NOT_SUPPORTED
        )
        return _blocked_plan(tool_id, target_raw, operation, reason)

    argument_digest = compute_argument_digest(tool_id, normalized)
    target_relative_path = normalized["targetPath"]

    # Validate the sandbox target path.
    ok, path_err, canonical = validate_sandbox_target_path(target_relative_path, hermes_home)
    if not ok or canonical is None:
        reason = _SANDBOX_ERR_TO_BLOCKED.get(path_err or "", BLOCKED_WRITE_TOOL_NOT_SUPPORTED)
        return _blocked_plan(
            tool_id, target_relative_path, operation, reason, argument_digest=argument_digest
        )

    before = safe_read_text(canonical)
    before_exists = before is not None
    before_hash = compute_sha256_text(before) if before is not None else None

    # Compute the prospective after-content (no write).
    warnings: list[str] = []
    if operation == "create_or_replace":
        after = normalized.get("content", "")
    elif operation == "append":
        after = (before or "") + normalized.get("content", "")
    elif operation == "patch":
        if before is None:
            return _blocked_plan(
                tool_id, target_relative_path, operation,
                BLOCKED_WRITE_PATCH_NO_UNIQUE_MATCH, argument_digest=argument_digest,
            )
        search = normalized.get("search", "")
        replace = normalized.get("replace", "")
        if before.count(search) != 1:
            return _blocked_plan(
                tool_id, target_relative_path, operation,
                BLOCKED_WRITE_PATCH_NO_UNIQUE_MATCH, argument_digest=argument_digest,
            )
        after = before.replace(search, replace, 1)
    else:  # readback — no write
        after = before or ""

    # Size / binary checks on the prospective content (readback skips these).
    content_being_written: str | None = None
    if operation == "create_or_replace":
        content_being_written = normalized.get("content", "")
        size_ok, size_err = validate_file_size_limits(content_being_written)
        if not size_ok:
            return _blocked_plan(
                tool_id, target_relative_path, operation,
                _SANDBOX_ERR_TO_BLOCKED.get(size_err or "", BLOCKED_WRITE_CONTENT_TOO_LARGE),
                argument_digest=argument_digest,
            )
    elif operation == "append":
        content_being_written = normalized.get("content", "")
        existing = len(before.encode("utf-8")) if before is not None else 0
        size_ok, size_err = validate_file_size_limits(
            content_being_written, existing_size=existing, append=True
        )
        if not size_ok:
            return _blocked_plan(
                tool_id, target_relative_path, operation,
                _SANDBOX_ERR_TO_BLOCKED.get(size_err or "", BLOCKED_WRITE_FILE_TOO_LARGE),
                argument_digest=argument_digest,
            )

    after_hash = compute_sha256_text(after) if after is not None else None
    content_digest = (
        compute_sha256_text(content_being_written) if content_being_written is not None else None
    )
    diff_preview = build_diff_preview(before, after)

    # Rollback preview.
    if operation == "readback":
        rollback_preview = "No write performed — rollback not required."
        manifest_mode = RESTORE_MODE_NONE
    else:
        manifest = build_rollback_manifest(
            operation=operation,
            target_relative_path=target_relative_path,
            before_content=before,
            after_content=after or "",
            after_hash=after_hash or "",
        )
        rollback_preview = manifest.restore_preview
        manifest_mode = manifest.restore_mode

    if operation != "readback" and manifest_mode == RESTORE_MODE_NONE:
        # A real write must always carry a rollback plan.
        return _blocked_plan(
            tool_id, target_relative_path, operation,
            BLOCKED_WRITE_MISSING_ROLLBACK_PLAN, argument_digest=argument_digest,
        )

    return WritePlan(
        write_plan_id=f"wpln_{uuid.uuid4().hex}",
        write_preview_id=f"wprv_{uuid.uuid4().hex}",
        tool_id=tool_id,
        operation=operation,
        sandbox_root_label=_SANDBOX_ROOT_LABEL,
        target_relative_path=target_relative_path,
        canonical_target_path=str(canonical),
        before_exists=before_exists,
        before_hash=before_hash,
        after_hash=after_hash,
        content_digest=content_digest,
        diff_preview=diff_preview,
        risk_tier=_WRITE_RISK_TIER,
        requires_confirmation=True,
        requires_write_enablement=True,
        rollback_preview=rollback_preview,
        blocked=False,
        blocked_reason=None,
        warnings=tuple(warnings),
        argument_digest=argument_digest,
        normalized_args=dict(normalized),
    )


def validate_write_plan(plan: WritePlan) -> tuple[bool, tuple[str, ...]]:
    """Validate a built plan's internal consistency. Returns ``(ok, errors)``."""
    errors: list[str] = []
    if plan.tool_id not in PHASE_2C_WRITE_TOOL_IDS:
        errors.append("plan tool_id is not a Phase 2C write tool")
    if not plan.write_plan_id.startswith("wpln_"):
        errors.append("plan write_plan_id malformed")
    if not plan.requires_confirmation:
        errors.append("write plan must require confirmation")
    if not plan.requires_write_enablement:
        errors.append("write plan must require write enablement")
    if not plan.blocked and plan.operation != "readback":
        if not plan.rollback_preview:
            errors.append("non-blocked write plan must carry a rollback preview")
        if not plan.after_hash:
            errors.append("non-blocked write plan must carry an after_hash")
    return (len(errors) == 0, tuple(errors))


def redact_write_plan_for_audit(plan: WritePlan) -> dict[str, Any]:
    """Return a redacted, audit-safe view of *plan* (no raw args / no secrets)."""
    safe = plan.to_safe_dict()
    # Defensive: never include raw args / canonical path / secrets in audit.
    safe.pop("canonicalTargetPath", None)
    safe.pop("normalizedArgs", None)
    for key in ("diffPreview", "rollbackPreview"):
        if isinstance(safe.get(key), str):
            safe[key] = _redact_text(safe[key])
    safe["argumentSummary"] = {
        "targetPath": plan.target_relative_path,
        "contentDigest": plan.content_digest,
        "contentLength": len(plan.normalized_args.get("content", "")) if isinstance(plan.normalized_args, Mapping) else 0,
    }
    safe["redactionApplied"] = True
    return safe


# ---------------------------------------------------------------------------
# 5. Confirmation token (stateless binding + in-memory single-use)
# ---------------------------------------------------------------------------

# Per-process nonce. Tokens are valid for the lifetime of the server process.
# File-backed TTL persistence + cross-process store are deferred to 2C-H1/2D.
_CONFIRMATION_NONCE = secrets.token_hex(32)
_CONSUMED_TOKENS: set[str] = set()


def _expected_confirmation_token(write_plan_id: str, argument_digest: str) -> str:
    raw = f"{write_plan_id}|{argument_digest}|{_CONFIRMATION_NONCE}"
    return "wctok_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def issue_write_confirmation_token(write_plan_id: str, argument_digest: str) -> str:
    """Issue a confirmation token bound to (write_plan_id, argument_digest)."""
    return _expected_confirmation_token(write_plan_id, argument_digest)


def verify_write_confirmation_token(
    raw_token: str | None,
    write_plan_id: str,
    argument_digest: str,
    *,
    consume: bool = True,
) -> tuple[bool, str | None]:
    """Verify a confirmation token. Returns ``(verified, error_code)``."""
    if not raw_token or not isinstance(raw_token, str):
        return False, BLOCKED_WRITE_CONFIRMATION_REQUIRED
    expected = _expected_confirmation_token(write_plan_id, argument_digest)
    if not secrets.compare_digest(raw_token, expected):
        return False, BLOCKED_WRITE_CONFIRMATION_REQUIRED
    if raw_token in _CONSUMED_TOKENS:
        return False, BLOCKED_WRITE_CONFIRMATION_REQUIRED
    if consume:
        _CONSUMED_TOKENS.add(raw_token)
    return True, None


def _reset_confirmation_state_for_tests() -> None:
    """Test-only hook to clear the in-memory consumed-token set."""
    _CONSUMED_TOKENS.clear()


# ---------------------------------------------------------------------------
# 6. Write preview (public envelope)
# ---------------------------------------------------------------------------


def build_write_preview(
    tool_id: str,
    normalized_args: Mapping[str, Any] | None,
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Build the public write preview envelope (dry-run). Issues a token.

    NEVER writes a file. Always safe to call even when write execution is
    disabled — the preview reflects what *would* happen and carries
    ``requiresWriteEnablement`` so the UI can gate the execute button.
    """
    plan = build_write_plan(tool_id, normalized_args, hermes_home=hermes_home)
    preview = plan.to_safe_dict()
    if not plan.blocked:
        token = issue_write_confirmation_token(plan.write_plan_id, plan.argument_digest)
        preview["confirmationToken"] = token
        preview["requiresUserConfirmation"] = True
        preview["writeExecuted"] = False
    else:
        preview["confirmationToken"] = None
        preview["requiresUserConfirmation"] = True
        preview["writeExecuted"] = False
    return preview


# ---------------------------------------------------------------------------
# 7. Provider write preview (preview-only; never auto-executes)
# ---------------------------------------------------------------------------


def _derive_provider_draft(message: str) -> tuple[str, str]:
    """Derive a deterministic sandbox draft (targetPath, content) from *message*."""
    digest = hashlib.sha256(message.strip().encode("utf-8")).hexdigest()[:12]
    safe_message = message.strip()
    if len(safe_message) > 1200:
        safe_message = safe_message[:1200] + "…"
    target = f"notes/provider-draft-{digest}.md"
    content = f"# Provider draft\n\n{safe_message}\n"
    return target, content


def build_provider_write_preview(
    message: str,
    tool_id: str,
    *,
    hermes_home: str | os.PathLike[str] | None = None,
    provider_mode: str = "fake",
) -> dict[str, Any]:
    """Generate a provider-suggested write preview. NEVER auto-executes.

    Returns an envelope with ``writeExecuted=False``,
    ``blockedReason=blocked_write_provider_auto_execute_denied``, and
    ``requiresUserConfirmation=True`` plus the full preview (so the user may
    manually confirm via the normal write path).
    """
    target, content = _derive_provider_draft(message)
    args: dict[str, Any] = {"targetPath": target, "content": content, "mode": "create_or_replace"}
    preview = build_write_preview(tool_id, args, hermes_home=hermes_home)
    preview["providerSuggested"] = True
    preview["providerToolCallParsed"] = True
    preview["writePreviewGenerated"] = True
    preview["writeExecuted"] = False
    preview["requiresUserConfirmation"] = True
    preview["blockedReason"] = BLOCKED_WRITE_PROVIDER_AUTO_EXECUTE_DENIED
    preview["providerMode"] = provider_mode
    return preview


# ---------------------------------------------------------------------------
# 8. Write audit writer
# ---------------------------------------------------------------------------

_PHASE = "2C"
_AUDIT_SCHEMA_VERSION = 1
_AUDIT_DIR_RELATIVE = "gateway/dev/audit"
_AUDIT_FILENAME = "tool-write-audit.jsonl"
_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"
_MAX_EVENT_BYTES = 32 * 1024
_MAX_FILE_BYTES = 5 * 1024 * 1024
_MAX_RETAINED_FILES = 3

# Event types.
EVENT_WRITE_PLAN_BUILT = "write_plan_built"
EVENT_WRITE_PREVIEW_GENERATED = "write_preview_generated"
EVENT_WRITE_CONFIRMATION_REQUIRED = "write_confirmation_required"
EVENT_WRITE_EXECUTION_BLOCKED = "write_execution_blocked"
EVENT_WRITE_PRE_EXECUTION_AUDIT = "write_pre_execution_audit"
EVENT_WRITE_HANDLER_CALLED = "write_handler_called"
EVENT_WRITE_POST_EXECUTION_AUDIT = "write_post_execution_audit"
EVENT_WRITE_ROLLBACK_MANIFEST_BUILT = "write_rollback_manifest_built"
EVENT_PROVIDER_WRITE_PREVIEW_GENERATED = "provider_write_preview_generated"
EVENT_PROVIDER_WRITE_AUTO_EXECUTE_BLOCKED = "provider_write_auto_execute_blocked"

ERROR_WRITE_AUDIT_HOME_MISSING = "WRITE_AUDIT_HERMES_HOME_MISSING"
ERROR_WRITE_AUDIT_PATH_OUTSIDE = "WRITE_AUDIT_PATH_OUTSIDE_HERMES_HOME"
ERROR_WRITE_AUDIT_TOO_LARGE = "WRITE_AUDIT_EVENT_TOO_LARGE"
ERROR_WRITE_AUDIT_WRITE_FAILED = "WRITE_AUDIT_WRITE_FAILED"
ERROR_WRITE_AUDIT_SERIALIZATION_FAILED = "WRITE_AUDIT_SERIALIZATION_FAILED"

_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
)
_FORBIDDEN_FIELD_STEMS: frozenset[str] = frozenset(
    n.replace("_", "").replace("-", "").lower()
    for n in (
        "api_key", "apikey", "authorization", "auth_header", "bearer",
        "token", "secret", "password", "passwd", "credential", "cookie",
        "session", "private_key", "client_secret", "access_token",
        "refresh_token", "access_key",
    )
)
_REDACTED_VALUE = "[REDACTED]"


def _redact_text(value: str) -> str:
    for pattern in _SECRET_VALUE_PATTERNS:
        value = pattern.sub(_REDACTED_VALUE, value)
    return value


def _is_forbidden_field(key: str) -> bool:
    if not isinstance(key, str):
        return True
    normalized = key.strip().lower().replace("_", "").replace("-", "")
    if normalized in _FORBIDDEN_FIELD_STEMS:
        return True
    return any(
        stem in normalized
        for stem in ("token", "secret", "password", "auth", "apikey", "privatekey", "credential")
    )


def _sanitize(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return None
    if isinstance(value, str):
        return _REDACTED_VALUE if _is_secret_string(value) else value
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, val in value.items():
            if _is_forbidden_field(key):
                out[str(key)] = _REDACTED_VALUE
                continue
            out[str(key)] = _sanitize(val, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [_sanitize(v, depth=depth + 1) for v in value]
    return "<non_json_value>"


def _is_secret_string(value: str) -> bool:
    for pattern in _SECRET_VALUE_PATTERNS:
        if pattern.search(value):
            return True
    return False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class WriteAuditWriteResult:
    written: bool
    event_id: str | None
    event_type: str
    path: str | None
    error_code: str | None
    error_message: str | None


def build_write_audit_event(
    *,
    event_type: str,
    tool_id: str | None,
    write_plan_id: str | None,
    write_preview_id: str | None,
    rollback_id: str | None,
    operation: str | None,
    target_relative_path: str | None,
    status: str | None,
    blocked_reason: str | None,
    payload: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a redacted write-audit event dict (not yet written)."""
    event: dict[str, Any] = {
        "eventId": f"wau_{uuid.uuid4().hex}",
        "eventType": event_type,
        "phase": _PHASE,
        "schemaVersion": _AUDIT_SCHEMA_VERSION,
        "timestamp": (now or datetime.now(timezone.utc)).isoformat(),
        "toolId": tool_id,
        "writePlanId": write_plan_id,
        "writePreviewId": write_preview_id,
        "rollbackId": rollback_id,
        "operation": operation,
        "targetRelativePath": target_relative_path,
        "status": status,
        "blockedReason": blocked_reason,
        "readOnly": False,
        "writeRequired": True,
        "localSideEffects": True,
        "externalSideEffects": False,
        "requiresConfirmation": True,
        "requiresWriteEnablement": True,
        "redactionApplied": True,
        "payload": dict(payload) if payload else {},
    }
    try:
        return _sanitize(event)
    except Exception:  # pragma: no cover — defensive
        event["payload"] = {}
        event["redactionApplied"] = True
        return event


def _resolve_audit_path(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, str | None]:
    if hermes_home is not None:
        home = Path(hermes_home).resolve()
    else:
        home_str = os.environ.get("HERMES_HOME", "")
        if not home_str:
            return Path(), ERROR_WRITE_AUDIT_HOME_MISSING
        home = Path(home_str).resolve()
    if home == Path(_PRODUCTION_HERMES_HOME).resolve():
        return Path(), ERROR_WRITE_AUDIT_PATH_OUTSIDE
    audit_path = home / _AUDIT_DIR_RELATIVE / _AUDIT_FILENAME
    try:
        audit_path.resolve().relative_to(home)
    except ValueError:
        return Path(), ERROR_WRITE_AUDIT_PATH_OUTSIDE
    return audit_path, None


def _rotate(audit_path: Path) -> None:
    try:
        if not audit_path.exists() or audit_path.stat().st_size < _MAX_FILE_BYTES:
            return
        base_dir = audit_path.parent
        base_name = audit_path.name
        oldest = base_dir / f"{base_name}.{_MAX_RETAINED_FILES - 1}"
        if oldest.exists():
            oldest.unlink()
        for i in range(_MAX_RETAINED_FILES - 2, 0, -1):
            src = base_dir / f"{base_name}.{i}"
            dst = base_dir / f"{base_name}.{i + 1}"
            if src.exists():
                src.rename(dst)
        audit_path.rename(base_dir / f"{base_name}.1")
    except OSError:
        return


def write_write_audit_event(
    event: Mapping[str, Any],
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> WriteAuditWriteResult:
    """Write one write-audit event to the dev JSONL file. Failures never enable execution."""
    event_type = str(event.get("eventType", "write_unknown"))
    event_id = event.get("eventId")
    audit_path, path_error = _resolve_audit_path(hermes_home)
    if path_error is not None:
        return WriteAuditWriteResult(
            written=False,
            event_id=event_id if isinstance(event_id, str) else None,
            event_type=event_type,
            path=None,
            error_code=path_error,
            error_message=_audit_message_for(path_error),
        )
    try:
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        return WriteAuditWriteResult(
            written=False,
            event_id=event_id if isinstance(event_id, str) else None,
            event_type=event_type,
            path=str(audit_path),
            error_code=ERROR_WRITE_AUDIT_SERIALIZATION_FAILED,
            error_message=f"serialization failed: {exc!s}",
        )
    line_bytes = (line + "\n").encode("utf-8")
    if len(line_bytes) > _MAX_EVENT_BYTES:
        marker = build_write_audit_event(
            event_type=event_type,
            tool_id=event.get("toolId"),
            write_plan_id=event.get("writePlanId"),
            write_preview_id=event.get("writePreviewId"),
            rollback_id=event.get("rollbackId"),
            operation=event.get("operation"),
            target_relative_path=event.get("targetRelativePath"),
            status="truncated",
            blocked_reason=None,
            payload={"truncated": True, "originalBytes": len(line_bytes)},
        )
        try:
            line_bytes = (json.dumps(marker, ensure_ascii=False) + "\n").encode("utf-8")
        except (TypeError, ValueError):
            return WriteAuditWriteResult(
                written=False, event_id=None, event_type=event_type,
                path=str(audit_path), error_code=ERROR_WRITE_AUDIT_TOO_LARGE,
                error_message="event too large and marker failed to serialize",
            )
    try:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        _rotate(audit_path)
        with audit_path.open("a", encoding="utf-8") as fh:
            fh.write(line_bytes.decode("utf-8"))
    except OSError as exc:
        return WriteAuditWriteResult(
            written=False,
            event_id=event_id if isinstance(event_id, str) else None,
            event_type=event_type,
            path=str(audit_path),
            error_code=ERROR_WRITE_AUDIT_WRITE_FAILED,
            error_message=f"write failed: {exc!s}",
        )
    return WriteAuditWriteResult(
        written=True,
        event_id=event_id if isinstance(event_id, str) else None,
        event_type=event_type,
        path=str(audit_path),
        error_code=None,
        error_message=None,
    )


def _audit_message_for(code: str) -> str:
    return {
        ERROR_WRITE_AUDIT_HOME_MISSING: "HERMES_HOME is not set.",
        ERROR_WRITE_AUDIT_PATH_OUTSIDE: "audit path is outside HERMES_HOME.",
        ERROR_WRITE_AUDIT_TOO_LARGE: "audit event exceeds the size cap.",
        ERROR_WRITE_AUDIT_WRITE_FAILED: "audit write failed.",
        ERROR_WRITE_AUDIT_SERIALIZATION_FAILED: "audit serialization failed.",
    }.get(code, "write audit error.")


def emit_write_audit(
    *,
    event_type: str,
    hermes_home: str | os.PathLike[str] | None,
    tool_id: str | None,
    write_plan_id: str | None,
    write_preview_id: str | None,
    rollback_id: str | None,
    operation: str | None,
    target_relative_path: str | None,
    status: str | None,
    blocked_reason: str | None,
    payload: Mapping[str, Any] | None = None,
) -> str | None:
    """Build + write one event; return its eventId (or None on failure)."""
    event = build_write_audit_event(
        event_type=event_type,
        tool_id=tool_id,
        write_plan_id=write_plan_id,
        write_preview_id=write_preview_id,
        rollback_id=rollback_id,
        operation=operation,
        target_relative_path=target_relative_path,
        status=status,
        blocked_reason=blocked_reason,
        payload=payload,
    )
    result = write_write_audit_event(event, hermes_home=hermes_home)
    return result.event_id if result.written else None
