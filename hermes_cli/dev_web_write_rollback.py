"""Phase 2C Write Rollback Manifest for the Hermes Dev WebUI.

Builds the rollback manifest for a controlled write inside the dev sandbox.
Phase 2C generates a rollback *manifest* and *preview*; automatic rollback
*execution* is deferred to Phase 2C-H1 / Phase 2D (a P2 item).

A rollback manifest records enough to describe how to undo a write:
  - If the target did not exist before the write, rollback = delete the file.
  - If the target existed, rollback = restore the previous content (identified
    by its ``beforeHash``).

The manifest deliberately does NOT embed the full prior content (which could
be large or secret-bearing). It carries hashes, sizes, and a bounded textual
preview. Audit redaction re-sanitizes the manifest before it is persisted.

Phase: 2C — Controlled Tool Write Execution (Dev Sandbox Write MVP)
Status: rollback manifest implemented (execution deferred)
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

RESTORE_MODE_DELETE_CREATED_FILE = "delete_created_file"
RESTORE_MODE_RESTORE_PREVIOUS_CONTENT = "restore_previous_content"
RESTORE_MODE_NONE = "none"

_PHASE = "2C"
_SCHEMA_VERSION = 1

_MAX_RESTORE_PREVIEW_CHARS = 240
_MAX_SNIPPET_CHARS = 240

# Secret value patterns — mirrored from the audit writers. The rollback
# manifest must never persist secrets even though it carries no full content.
_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
)
_REDACTED_VALUE = "[REDACTED]"


# ---------------------------------------------------------------------------
# 2. Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RollbackManifest:
    """Immutable rollback manifest for one controlled write."""

    rollback_id: str
    operation: str
    target_relative_path: str
    before_exists: bool
    before_hash: str | None
    after_hash: str
    before_size_bytes: int
    after_size_bytes: int
    restore_mode: str
    restore_preview: str
    created_at: str
    schema_version: int = _SCHEMA_VERSION
    phase: str = _PHASE
    extra: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rollbackId": self.rollback_id,
            "operation": self.operation,
            "targetRelativePath": self.target_relative_path,
            "beforeExists": self.before_exists,
            "beforeHash": self.before_hash,
            "afterHash": self.after_hash,
            "beforeSizeBytes": self.before_size_bytes,
            "afterSizeBytes": self.after_size_bytes,
            "restoreMode": self.restore_mode,
            "restorePreview": self.restore_preview,
            "createdAt": self.created_at,
            "schemaVersion": self.schema_version,
            "phase": self.phase,
        }


# ---------------------------------------------------------------------------
# 3. Builders
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_text(value: str) -> str:
    redacted = value
    for pattern in _SECRET_VALUE_PATTERNS:
        redacted = pattern.sub(_REDACTED_VALUE, redacted)
    return redacted


def _bounded_snippet(content: str | None) -> str:
    if not content:
        return ""
    snippet = content[:_MAX_SNIPPET_CHARS]
    if len(content) > _MAX_SNIPPET_CHARS:
        snippet += "…"
    return _redact_text(snippet)


def build_rollback_manifest(
    *,
    operation: str,
    target_relative_path: str,
    before_content: str | None,
    after_content: str,
    after_hash: str,
) -> RollbackManifest:
    """Build a rollback manifest for a completed write.

    ``before_content`` is ``None`` when the target did not previously exist.
    """
    before_exists = before_content is not None
    before_hash = None
    before_size = 0
    if before_content is not None:
        from hermes_cli.dev_web_write_sandbox import compute_sha256_text

        before_hash = compute_sha256_text(before_content)
        before_size = len(before_content.encode("utf-8"))

    after_size = len(after_content.encode("utf-8")) if after_content else 0

    if not before_exists:
        restore_mode = RESTORE_MODE_DELETE_CREATED_FILE
        restore_preview = (
            f"Rollback would delete the newly-created file "
            f"'{_redact_text(target_relative_path)}'."
        )
    else:
        restore_mode = RESTORE_MODE_RESTORE_PREVIOUS_CONTENT
        restore_preview = (
            f"Rollback would restore '{_redact_text(target_relative_path)}' to "
            f"its previous content (beforeHash={before_hash}, "
            f"{before_size} bytes)."
        )

    restore_preview = restore_preview[:_MAX_RESTORE_PREVIEW_CHARS]

    return RollbackManifest(
        rollback_id=f"wrbk_{uuid.uuid4().hex}",
        operation=operation,
        target_relative_path=target_relative_path,
        before_exists=before_exists,
        before_hash=before_hash,
        after_hash=after_hash,
        before_size_bytes=before_size,
        after_size_bytes=after_size,
        restore_mode=restore_mode,
        restore_preview=restore_preview,
        created_at=_now_iso(),
    )


# ---------------------------------------------------------------------------
# 4. Validation + audit redaction
# ---------------------------------------------------------------------------


def validate_rollback_manifest(manifest: RollbackManifest | Mapping[str, Any]) -> tuple[bool, tuple[str, ...]]:
    """Validate a rollback manifest. Returns ``(valid, errors)``."""
    data = manifest.to_dict() if isinstance(manifest, RollbackManifest) else dict(manifest)
    errors: list[str] = []
    required_str = (
        "rollbackId", "operation", "targetRelativePath", "afterHash",
        "restoreMode", "restorePreview", "createdAt",
    )
    for key in required_str:
        if not isinstance(data.get(key), str) or not data.get(key):
            errors.append(f"rollback manifest missing required field: {key}")
    if data.get("restoreMode") not in (
        RESTORE_MODE_DELETE_CREATED_FILE,
        RESTORE_MODE_RESTORE_PREVIOUS_CONTENT,
        RESTORE_MODE_NONE,
    ):
        errors.append(f"rollback manifest has invalid restoreMode: {data.get('restoreMode')!r}")
    if not isinstance(data.get("beforeExists"), bool):
        errors.append("rollback manifest beforeExists must be a boolean")
    # No raw secrets may appear anywhere in the manifest.
    blob = repr(data)
    for pattern in _SECRET_VALUE_PATTERNS:
        if pattern.search(blob):
            errors.append("rollback manifest contains a secret pattern")
            break
    return (len(errors) == 0, tuple(errors))


def redact_rollback_manifest_for_audit(manifest: RollbackManifest | Mapping[str, Any]) -> dict[str, Any]:
    """Return a safe, redacted dict of the manifest for audit persistence."""
    data = manifest.to_dict() if isinstance(manifest, RollbackManifest) else dict(manifest)
    safe: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            safe[key] = _redact_text(value)
        elif isinstance(value, bool):
            safe[key] = value
        elif isinstance(value, int):
            safe[key] = value
        else:
            safe[key] = value
    safe["redactionApplied"] = True
    return safe


# ---------------------------------------------------------------------------
# 5. Rollback EXECUTION (Phase 2C-H1)
# ---------------------------------------------------------------------------
#
# Phase 2C generated rollback manifests; Phase 2C-H1 executes them. Execution
# loads a stored manifest, verifies the current sandbox state matches the
# manifest's afterHash, and either deletes a created file or restores the
# previous content. It is gated by write enablement + a rollback-scoped
# confirmation token + digest verification, and fully audited.

# Rollback execution blocked reasons.
BLOCKED_ROLLBACK_MANIFEST_NOT_FOUND = "blocked_rollback_manifest_not_found"
BLOCKED_ROLLBACK_ALREADY_EXECUTED = "blocked_rollback_already_executed"
BLOCKED_ROLLBACK_CURRENT_HASH_MISMATCH = "blocked_rollback_current_hash_mismatch"
BLOCKED_ROLLBACK_MANIFEST_TAMPERED = "blocked_rollback_manifest_tampered"
BLOCKED_ROLLBACK_TARGET_ESCAPE = "blocked_rollback_target_escape"
BLOCKED_ROLLBACK_SYMLINK_ESCAPE = "blocked_rollback_symlink_escape"
BLOCKED_ROLLBACK_CONFIRMATION_REQUIRED = "blocked_rollback_confirmation_required"
BLOCKED_ROLLBACK_DIGEST_MISMATCH = "blocked_rollback_digest_mismatch"
BLOCKED_ROLLBACK_WRITE_NOT_ENABLED = "blocked_rollback_write_not_enabled"
BLOCKED_ROLLBACK_FORBIDDEN_TARGET = "blocked_rollback_forbidden_target"

_SANDBOX_ERR_TO_ROLLBACK = {
    "blocked_write_path_traversal": BLOCKED_ROLLBACK_TARGET_ESCAPE,
    "blocked_write_absolute_path": BLOCKED_ROLLBACK_TARGET_ESCAPE,
    "blocked_write_symlink_escape": BLOCKED_ROLLBACK_SYMLINK_ESCAPE,
    "blocked_write_forbidden_path": BLOCKED_ROLLBACK_FORBIDDEN_TARGET,
    "blocked_write_file_type": BLOCKED_ROLLBACK_FORBIDDEN_TARGET,
}


@dataclass(frozen=True, slots=True)
class RollbackExecutionPlan:
    """Dry-run plan for executing one rollback."""

    rollback_id: str
    operation: str
    target_relative_path: str
    restore_mode: str
    before_exists: bool
    before_hash: str | None
    after_hash: str
    current_hash: str
    restore_preview: str
    argument_digest: str
    blocked: bool
    blocked_reason: str | None

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "rollbackId": self.rollback_id,
            "operation": self.operation,
            "targetRelativePath": self.target_relative_path,
            "restoreMode": self.restore_mode,
            "beforeExists": self.before_exists,
            "beforeHash": self.before_hash,
            "afterHash": self.after_hash,
            "currentHash": self.current_hash,
            "expectedCurrentHash": self.after_hash,
            "restorePreview": self.restore_preview,
            "argumentDigest": self.argument_digest,
            "readOnly": False,
            "writeRequired": True,
            "localSideEffects": True,
            "externalSideEffects": False,
            "requiresConfirmation": True,
            "requiresWriteEnablement": True,
            "blocked": self.blocked,
            "blockedReason": self.blocked_reason,
        }


def compute_rollback_argument_digest(
    rollback_id: str, target_relative_path: str, expected_current_hash: str
) -> str:
    """Stable digest binding a rollback execution to (rollbackId, target, hash)."""
    import hashlib
    import json

    canonical = json.dumps(
        {"rollbackId": rollback_id, "target": target_relative_path, "hash": expected_current_hash},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _blocked_rollback_plan(
    rollback_id: str,
    *,
    operation: str,
    target_relative_path: str,
    after_hash: str,
    reason: str,
) -> RollbackExecutionPlan:
    return RollbackExecutionPlan(
        rollback_id=rollback_id,
        operation=operation,
        target_relative_path=target_relative_path,
        restore_mode=RESTORE_MODE_NONE,
        before_exists=False,
        before_hash=None,
        after_hash=after_hash,
        current_hash="",
        restore_preview="",
        argument_digest="",
        blocked=True,
        blocked_reason=reason,
    )


def build_rollback_execution_plan(
    rollback_id: str,
    *,
    hermes_home: str | None = None,
) -> RollbackExecutionPlan:
    """Build a rollback execution plan from a stored manifest. NEVER writes.

    Loads the manifest, validates it, checks the current sandbox file state
    matches the manifest's ``afterHash``, and returns the plan (or a blocked
    plan with a precise reason).
    """
    from hermes_cli.dev_web_write_rollback_store import (
        is_valid_rollback_id,
        load_rollback_manifest,
        validate_rollback_manifest_for_execution,
    )
    from hermes_cli.dev_web_write_sandbox import (
        compute_sha256_text,
        safe_read_text,
        validate_sandbox_target_path,
    )

    if not is_valid_rollback_id(rollback_id):
        return _blocked_rollback_plan(
            rollback_id, operation="rollback", target_relative_path="",
            after_hash="", reason=BLOCKED_ROLLBACK_MANIFEST_NOT_FOUND,
        )

    data = load_rollback_manifest(rollback_id, hermes_home=hermes_home)
    if data is None:
        return _blocked_rollback_plan(
            rollback_id, operation="rollback", target_relative_path="",
            after_hash="", reason=BLOCKED_ROLLBACK_MANIFEST_NOT_FOUND,
        )

    ok, _errors = validate_rollback_manifest_for_execution(data)
    if not ok:
        return _blocked_rollback_plan(
            rollback_id, operation=str(data.get("operation", "rollback")),
            target_relative_path=str(data.get("targetRelativePath", "")),
            after_hash=str(data.get("afterHash", "")),
            reason=BLOCKED_ROLLBACK_MANIFEST_TAMPERED,
        )

    if data.get("executed") is True:
        return _blocked_rollback_plan(
            rollback_id, operation=str(data.get("operation", "rollback")),
            target_relative_path=str(data.get("targetRelativePath", "")),
            after_hash=str(data.get("afterHash", "")),
            reason=BLOCKED_ROLLBACK_ALREADY_EXECUTED,
        )

    target_relative_path = str(data.get("targetRelativePath", ""))
    after_hash = str(data.get("afterHash", ""))
    restore_mode = str(data.get("restoreMode", RESTORE_MODE_NONE))

    # Validate the sandbox target.
    path_ok, path_err, canonical = validate_sandbox_target_path(target_relative_path, hermes_home)
    if not path_ok or canonical is None:
        reason = _SANDBOX_ERR_TO_ROLLBACK.get(path_err or "", BLOCKED_ROLLBACK_TARGET_ESCAPE)
        return _blocked_rollback_plan(
            rollback_id, operation=str(data.get("operation", "rollback")),
            target_relative_path=target_relative_path, after_hash=after_hash, reason=reason,
        )

    current = safe_read_text(canonical)
    current_hash = compute_sha256_text(current) if current is not None else ""
    if current is None or current_hash != after_hash:
        return _blocked_rollback_plan(
            rollback_id, operation=str(data.get("operation", "rollback")),
            target_relative_path=target_relative_path, after_hash=after_hash,
            reason=BLOCKED_ROLLBACK_CURRENT_HASH_MISMATCH,
        )

    before_exists = bool(data.get("beforeExists"))
    before_hash = data.get("beforeHash")
    if restore_mode == RESTORE_MODE_DELETE_CREATED_FILE:
        restore_preview = (
            f"Rollback would delete the created file '{_redact_text(target_relative_path)}'."
        )
    else:
        restore_preview = (
            f"Rollback would restore '{_redact_text(target_relative_path)}' to its previous "
            f"content (beforeHash={before_hash})."
        )

    argument_digest = compute_rollback_argument_digest(rollback_id, target_relative_path, after_hash)
    return RollbackExecutionPlan(
        rollback_id=rollback_id,
        operation=str(data.get("operation", "rollback")),
        target_relative_path=target_relative_path,
        restore_mode=restore_mode,
        before_exists=before_exists,
        before_hash=before_hash if isinstance(before_hash, str) else None,
        after_hash=after_hash,
        current_hash=current_hash,
        restore_preview=restore_preview[:_MAX_RESTORE_PREVIEW_CHARS],
        argument_digest=argument_digest,
        blocked=False,
        blocked_reason=None,
    )


def build_rollback_execution_preview(
    rollback_id: str,
    *,
    hermes_home: str | None = None,
) -> dict[str, Any]:
    """Public rollback preview envelope. Issues a rollback-scoped token."""
    from hermes_cli.dev_web_confirmation_store import (
        SCOPE_ROLLBACK_EXECUTE,
        DEFAULT_TTL_ROLLBACK_SECONDS,
        create_confirmation_token,
    )

    plan = build_rollback_execution_plan(rollback_id, hermes_home=hermes_home)
    preview = plan.to_safe_dict()
    preview["sandboxOnly"] = True
    preview["requiresUserConfirmation"] = True
    if not plan.blocked:
        issue = create_confirmation_token(
            {
                "rollbackId": plan.rollback_id,
                "targetRelativePath": plan.target_relative_path,
                "restoreMode": plan.restore_mode,
            },
            scope=SCOPE_ROLLBACK_EXECUTE,
            argument_digest=plan.argument_digest,
            tool_id="dev_sandbox_rollback_execute",
            operation="rollback",
            ttl_seconds=DEFAULT_TTL_ROLLBACK_SECONDS,
            hermes_home=hermes_home,
        )
        preview["confirmationToken"] = issue.token if issue else None
        preview["confirmationTokenScope"] = SCOPE_ROLLBACK_EXECUTE
    else:
        preview["confirmationToken"] = None
        preview["confirmationTokenScope"] = None
    return preview
