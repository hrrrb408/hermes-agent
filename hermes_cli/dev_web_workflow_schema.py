"""Phase 3A Dev-only Agent Workflow Schema for the Hermes Dev WebUI.

This module is the single metadata source for the dev-only, manual,
approval-gated Agent Workflow MVP. It defines:

  - the workflow schema version (``workflow_schema_v1``)
  - the allowed / forbidden workflow step types
  - the workflow step status lifecycle
  - the immutable workflow data records (definition, plan, step, execution
    state, timeline event, approval gate, audit link, safety boundary)
  - the blocked-reason catalogue (``blocked_workflow_*``)
  - strict input sanitization (no secrets / tokens / paths / callables)

Phase 3A constraints (frozen):
  - dev-only; manual step execution only; approval-gated; audit-linked
  - rollback-reference only; fake-provider only; sandbox write PREVIEW only
  - no autonomous write, no write execution, no rollback execution
  - no real provider, no shell, no database mutation, no external service write
  - no production rollout, no ``~/.hermes`` / production ``state.db`` access
  - stdlib only; no provider / handler / dispatch / agent runtime imports
  - never stores raw arguments, raw tokens, full token hashes, file content,
    API keys, callable reprs, or production paths

Phase: 3A — Dev-only Agent Workflow MVP
Status: workflow schema v1 implemented
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


# ---------------------------------------------------------------------------
# 1. Schema version + id prefixes
# ---------------------------------------------------------------------------

#: Canonical schema version tag for every workflow document.
WORKFLOW_SCHEMA_VERSION = "workflow_schema_v1"

WORKFLOW_ID_PREFIX = "wf_"
WORKFLOW_PLAN_ID_PREFIX = "wfp_"
WORKFLOW_STEP_ID_PREFIX = "wfs_"
WORKFLOW_EXECUTION_ID_PREFIX = "wfx_"
WORKFLOW_AUDIT_ID_PREFIX = "wfa_"
WORKFLOW_APPROVAL_ID_PREFIX = "wfap_"

# Bounded lengths — workflow documents are intentionally small.
_MAX_TITLE_LENGTH = 200
_MAX_DESCRIPTION_LENGTH = 2000
_MAX_GOAL_LENGTH = 2000
_MAX_NOTE_LENGTH = 2000
_MAX_STEPS = 32
_MAX_STEP_TITLE_LENGTH = 200
_MAX_MESSAGE_LENGTH = 4000
_MAX_ALLOWED_TOOLS = 32
_MAX_ALLOWED_TOOL_NAME_LENGTH = 128
_MAX_TARGET_PATH_LENGTH = 512
_MAX_CONTENT_PREVIEW_LENGTH = 2000
_MAX_METADATA_ITEMS = 32
_MAX_METADATA_VALUE_LENGTH = 512

_ID_HEX_RE = re.compile(r"^[a-z]+_[0-9a-f]{12,64}$")


def new_workflow_id(prefix: str) -> str:
    """Generate a new workflow id with the given prefix.

    Workflow ids are public correlation ids (not secrets), so a time + hash is
    sufficient and keeps this module import-clean (no ``secrets`` dependency).
    The approval layer uses ``secrets`` for the real single-use tokens.
    """
    import hashlib
    import time

    raw = f"{prefix}{time.time_ns():x}{hashlib.sha1(str(time.time()).encode()).hexdigest()[:16]}"
    return f"{prefix}{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:20]}"


def is_valid_workflow_id(value: Any, prefix: str) -> bool:
    """Return ``True`` if *value* is a valid prefixed workflow id."""
    return (
        isinstance(value, str)
        and value.startswith(prefix)
        and bool(_ID_HEX_RE.match(value))
    )


# ---------------------------------------------------------------------------
# 2. Step types (allowed + forbidden)
# ---------------------------------------------------------------------------

#: The ONLY step types Phase 3A permits inside a workflow plan.
STEP_READ_ONLY_TOOL = "read_only_tool"
STEP_FAKE_PROVIDER_ROUNDTRIP = "fake_provider_roundtrip"
STEP_SANDBOX_WRITE_PREVIEW = "sandbox_write_preview"
STEP_ROLLBACK_REFERENCE = "rollback_reference"
STEP_MANUAL_NOTE = "manual_note"
STEP_AUDIT_QUERY = "audit_query"

ALLOWED_STEP_TYPES: frozenset[str] = frozenset(
    {
        STEP_READ_ONLY_TOOL,
        STEP_FAKE_PROVIDER_ROUNDTRIP,
        STEP_SANDBOX_WRITE_PREVIEW,
        STEP_ROLLBACK_REFERENCE,
        STEP_MANUAL_NOTE,
        STEP_AUDIT_QUERY,
    }
)

#: Step types that are PERMANENTLY blocked. Any attempt to build / execute one
#: of these must be rejected with the matching blocked reason.
STEP_REAL_PROVIDER_ROUNDTRIP = "real_provider_roundtrip"
STEP_PROVIDER_WRITE_EXECUTE = "provider_write_execute"
STEP_SANDBOX_WRITE_EXECUTE = "sandbox_write_execute"
STEP_ROLLBACK_EXECUTE = "rollback_execute"
STEP_SHELL_COMMAND = "shell_command"
STEP_DATABASE_QUERY = "database_query"
STEP_DATABASE_MUTATION = "database_mutation"
STEP_EXTERNAL_HTTP_REQUEST = "external_http_request"
STEP_FILE_DELETE = "file_delete"
STEP_FILE_RENAME = "file_rename"
STEP_FILE_CHMOD = "file_chmod"
STEP_PLUGIN_DYNAMIC_LOAD = "plugin_dynamic_load"
STEP_BACKGROUND_AGENT = "background_agent"
STEP_SCHEDULED_TASK = "scheduled_task"
STEP_PRODUCTION_OPERATION = "production_operation"

FORBIDDEN_STEP_TYPES: frozenset[str] = frozenset(
    {
        STEP_REAL_PROVIDER_ROUNDTRIP,
        STEP_PROVIDER_WRITE_EXECUTE,
        STEP_SANDBOX_WRITE_EXECUTE,
        STEP_ROLLBACK_EXECUTE,
        STEP_SHELL_COMMAND,
        STEP_DATABASE_QUERY,
        STEP_DATABASE_MUTATION,
        STEP_EXTERNAL_HTTP_REQUEST,
        STEP_FILE_DELETE,
        STEP_FILE_RENAME,
        STEP_FILE_CHMOD,
        STEP_PLUGIN_DYNAMIC_LOAD,
        STEP_BACKGROUND_AGENT,
        STEP_SCHEDULED_TASK,
        STEP_PRODUCTION_OPERATION,
    }
)

#: Map each forbidden step type to its precise blocked reason. Defined after
#: the blocked-reason constants in section 3 (see ``_FORBIDDEN_STEP_MAP``) so
#: every referenced constant already exists at module load time.


# ---------------------------------------------------------------------------
# 3. Blocked-reason catalogue
# ---------------------------------------------------------------------------

# Step-type / capability blocked reasons (section 7 of the brief).
BLOCKED_REAL_PROVIDER = "blocked_workflow_real_provider_not_allowed"
BLOCKED_AUTONOMOUS_WRITE = "blocked_workflow_autonomous_write_not_allowed"
BLOCKED_PROVIDER_WRITE = "blocked_workflow_provider_write_not_allowed"
BLOCKED_ROLLBACK_EXECUTE = "blocked_workflow_rollback_execute_not_allowed"
BLOCKED_SHELL = "blocked_workflow_shell_not_allowed"
BLOCKED_DATABASE = "blocked_workflow_database_not_allowed"
BLOCKED_EXTERNAL_SERVICE = "blocked_workflow_external_service_not_allowed"
BLOCKED_PRODUCTION = "blocked_workflow_production_not_allowed"
BLOCKED_PLUGIN_DYNAMIC_LOAD = "blocked_workflow_plugin_dynamic_load_not_allowed"
BLOCKED_STEP_TYPE_NOT_ALLOWED = "blocked_workflow_step_type_not_allowed"

# Approval-gate blocked reasons (section 12 of the brief).
BLOCKED_APPROVAL_REQUIRED = "blocked_workflow_approval_required"
BLOCKED_APPROVAL_EXPIRED = "blocked_workflow_approval_expired"
BLOCKED_APPROVAL_SCOPE_MISMATCH = "blocked_workflow_approval_scope_mismatch"
BLOCKED_APPROVAL_STEP_MISMATCH = "blocked_workflow_approval_step_mismatch"
BLOCKED_APPROVAL_DIGEST_MISMATCH = "blocked_workflow_approval_digest_mismatch"
BLOCKED_APPROVAL_ALREADY_USED = "blocked_workflow_approval_already_used"

# Plan-time blocked reasons (unsafe input).
BLOCKED_UNSAFE_PATH = "blocked_workflow_unsafe_path_not_allowed"
BLOCKED_SECRET_INPUT = "blocked_workflow_secret_input_not_allowed"
BLOCKED_RAW_TOKEN_INPUT = "blocked_workflow_raw_token_input_not_allowed"
BLOCKED_INVALID_INPUT = "blocked_workflow_invalid_input"
BLOCKED_STORE_UNAVAILABLE = "blocked_workflow_store_unavailable"

#: All workflow blocked-reason codes (used by the frontend catalogue).
WORKFLOW_BLOCKED_REASONS: frozenset[str] = frozenset(
    {
        BLOCKED_REAL_PROVIDER,
        BLOCKED_AUTONOMOUS_WRITE,
        BLOCKED_PROVIDER_WRITE,
        BLOCKED_ROLLBACK_EXECUTE,
        BLOCKED_SHELL,
        BLOCKED_DATABASE,
        BLOCKED_EXTERNAL_SERVICE,
        BLOCKED_PRODUCTION,
        BLOCKED_PLUGIN_DYNAMIC_LOAD,
        BLOCKED_STEP_TYPE_NOT_ALLOWED,
        BLOCKED_APPROVAL_REQUIRED,
        BLOCKED_APPROVAL_EXPIRED,
        BLOCKED_APPROVAL_SCOPE_MISMATCH,
        BLOCKED_APPROVAL_STEP_MISMATCH,
        BLOCKED_APPROVAL_DIGEST_MISMATCH,
        BLOCKED_APPROVAL_ALREADY_USED,
        BLOCKED_UNSAFE_PATH,
        BLOCKED_SECRET_INPUT,
        BLOCKED_RAW_TOKEN_INPUT,
        BLOCKED_INVALID_INPUT,
        BLOCKED_STORE_UNAVAILABLE,
    }
)

#: Map each forbidden step type to its precise blocked reason. Every value is a
#: ``blocked_workflow_*`` constant defined above.
FORBIDDEN_STEP_BLOCKED_REASONS: Mapping[str, str] = MappingProxyType(
    {
        STEP_REAL_PROVIDER_ROUNDTRIP: BLOCKED_REAL_PROVIDER,
        STEP_PROVIDER_WRITE_EXECUTE: BLOCKED_PROVIDER_WRITE,
        STEP_SANDBOX_WRITE_EXECUTE: BLOCKED_AUTONOMOUS_WRITE,
        STEP_ROLLBACK_EXECUTE: BLOCKED_ROLLBACK_EXECUTE,
        STEP_SHELL_COMMAND: BLOCKED_SHELL,
        STEP_DATABASE_QUERY: BLOCKED_DATABASE,
        STEP_DATABASE_MUTATION: BLOCKED_DATABASE,
        STEP_EXTERNAL_HTTP_REQUEST: BLOCKED_EXTERNAL_SERVICE,
        STEP_FILE_DELETE: BLOCKED_AUTONOMOUS_WRITE,
        STEP_FILE_RENAME: BLOCKED_AUTONOMOUS_WRITE,
        STEP_FILE_CHMOD: BLOCKED_AUTONOMOUS_WRITE,
        STEP_PLUGIN_DYNAMIC_LOAD: BLOCKED_PLUGIN_DYNAMIC_LOAD,
        STEP_BACKGROUND_AGENT: BLOCKED_AUTONOMOUS_WRITE,
        STEP_SCHEDULED_TASK: BLOCKED_AUTONOMOUS_WRITE,
        STEP_PRODUCTION_OPERATION: BLOCKED_PRODUCTION,
    }
)


def blocked_reason_for_step_type(step_type: str) -> str | None:
    """Return the blocked reason for a forbidden step type, or ``None``."""
    return FORBIDDEN_STEP_BLOCKED_REASONS.get(step_type)


# ---------------------------------------------------------------------------
# 4. Step status lifecycle
# ---------------------------------------------------------------------------

STATUS_DRAFT = "draft"
STATUS_PLANNED = "planned"
STATUS_PREVIEWED = "previewed"
STATUS_APPROVAL_REQUIRED = "approval_required"
STATUS_APPROVED = "approved"
STATUS_READY = "ready"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_BLOCKED = "blocked"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

VALID_STEP_STATUSES: frozenset[str] = frozenset(
    {
        STATUS_DRAFT,
        STATUS_PLANNED,
        STATUS_PREVIEWED,
        STATUS_APPROVAL_REQUIRED,
        STATUS_APPROVED,
        STATUS_READY,
        STATUS_RUNNING,
        STATUS_COMPLETED,
        STATUS_BLOCKED,
        STATUS_FAILED,
        STATUS_SKIPPED,
    }
)

#: Workflow execution-level status (coarser than per-step status).
EXEC_STATUS_DRAFT = "draft"
EXEC_STATUS_RUNNING = "running"
EXEC_STATUS_PAUSED = "paused"
EXEC_STATUS_COMPLETED = "completed"
EXEC_STATUS_FAILED = "failed"

VALID_EXECUTION_STATUSES: frozenset[str] = frozenset(
    {
        EXEC_STATUS_DRAFT,
        EXEC_STATUS_RUNNING,
        EXEC_STATUS_PAUSED,
        EXEC_STATUS_COMPLETED,
        EXEC_STATUS_FAILED,
    }
)


# ---------------------------------------------------------------------------
# 5. Provider mode (fake only in Phase 3A)
# ---------------------------------------------------------------------------

PROVIDER_MODE_DISABLED = "disabled"
PROVIDER_MODE_FAKE = "fake"
PROVIDER_MODE_REAL = "real"

ALLOWED_PROVIDER_MODES: frozenset[str] = frozenset(
    {PROVIDER_MODE_DISABLED, PROVIDER_MODE_FAKE}
)


# ---------------------------------------------------------------------------
# 6. Phase / source tags for workflow audit events
# ---------------------------------------------------------------------------

WORKFLOW_PHASE = "3A"
WORKFLOW_AUDIT_SOURCE = "workflow_api"

# Workflow audit event types (section 13 of the brief).
EVENT_WORKFLOW_PLAN_CREATED = "workflow_plan_created"
EVENT_WORKFLOW_PLAN_BLOCKED = "workflow_plan_blocked"
EVENT_WORKFLOW_EXECUTION_CREATED = "workflow_execution_created"
EVENT_WORKFLOW_STEP_PREVIEW_CREATED = "workflow_step_preview_created"
EVENT_WORKFLOW_STEP_APPROVAL_CREATED = "workflow_step_approval_created"
EVENT_WORKFLOW_STEP_APPROVAL_USED = "workflow_step_approval_used"
EVENT_WORKFLOW_STEP_STARTED = "workflow_step_started"
EVENT_WORKFLOW_STEP_COMPLETED = "workflow_step_completed"
EVENT_WORKFLOW_STEP_BLOCKED = "workflow_step_blocked"
EVENT_WORKFLOW_STEP_FAILED = "workflow_step_failed"
EVENT_WORKFLOW_TIMELINE_UPDATED = "workflow_timeline_updated"
EVENT_WORKFLOW_EXECUTION_COMPLETED = "workflow_execution_completed"

VALID_WORKFLOW_EVENT_TYPES: frozenset[str] = frozenset(
    {
        EVENT_WORKFLOW_PLAN_CREATED,
        EVENT_WORKFLOW_PLAN_BLOCKED,
        EVENT_WORKFLOW_EXECUTION_CREATED,
        EVENT_WORKFLOW_STEP_PREVIEW_CREATED,
        EVENT_WORKFLOW_STEP_APPROVAL_CREATED,
        EVENT_WORKFLOW_STEP_APPROVAL_USED,
        EVENT_WORKFLOW_STEP_STARTED,
        EVENT_WORKFLOW_STEP_COMPLETED,
        EVENT_WORKFLOW_STEP_BLOCKED,
        EVENT_WORKFLOW_STEP_FAILED,
        EVENT_WORKFLOW_TIMELINE_UPDATED,
        EVENT_WORKFLOW_EXECUTION_COMPLETED,
    }
)


# ---------------------------------------------------------------------------
# 7. Input sanitizer (no secrets / tokens / paths / callables)
# ---------------------------------------------------------------------------

_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
)
_REDACTED_VALUE = "[REDACTED]"

_FORBIDDEN_FIELD_STEMS: frozenset[str] = frozenset(
    n.replace("_", "").replace("-", "").lower()
    for n in (
        "api_key", "apikey", "authorization", "auth_header", "bearer",
        "token", "secret", "password", "passwd", "credential", "cookie",
        "session", "private_key", "client_secret", "access_token",
        "refresh_token", "access_key", "apikey",
    )
)

#: Keys that may never appear in workflow step input (raw material carriers).
_FORBIDDEN_INPUT_KEYS: frozenset[str] = frozenset(
    {
        "rawArguments", "rawArgs", "fullTokenHash", "tokenSecret",
        "plainToken", "rawToken", "apiKey", "api_key", "authorization",
        "bearer", "password", "secret", "credential", "cookie",
        "callable", "handler", "sourcePath", "absolutePath",
    }
)


def _is_secret_string(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS)


def redact_secret_strings(value: Any) -> Any:
    """Recursively replace secret-looking string values with ``[REDACTED]``."""
    if isinstance(value, str):
        return _REDACTED_VALUE if _is_secret_string(value) else value
    if isinstance(value, dict):
        return {k: redact_secret_strings(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_secret_strings(v) for v in value]
    if isinstance(value, tuple):
        return tuple(redact_secret_strings(v) for v in value)
    return value


def contains_secret_material(value: Any) -> bool:
    """Return ``True`` if any nested string looks like a secret / API key.

    Used by the planner to BLOCK secret-like input (rather than silently
    redacting it) so an operator knows their step carried disallowed material.
    """
    if isinstance(value, str):
        return _is_secret_string(value)
    if isinstance(value, dict):
        return any(contains_secret_material(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(contains_secret_material(v) for v in value)
    return False


def is_forbidden_input_key(key: Any) -> bool:
    """Return ``True`` if *key* is a forbidden workflow-input field."""
    if not isinstance(key, str):
        return True
    normalized = key.strip().lower().replace("-", "").replace("_", "")
    # Exact forbidden input keys (raw token / hash / arg / callable carriers).
    forbidden_normalized = {
        n.replace("_", "").replace("-", "").lower() for n in _FORBIDDEN_INPUT_KEYS
    }
    if normalized in forbidden_normalized:
        return True
    if normalized in _FORBIDDEN_FIELD_STEMS:
        return True
    return any(stem in normalized for stem in ("token", "secret", "password", "apikey"))


def contains_unsafe_path(value: str) -> bool:
    """Return ``True`` if *value* resembles an absolute / traversal / home path."""
    if not isinstance(value, str) or not value:
        return False
    if value.startswith(("/", "~", "\\")):
        return True
    if ".." in value:
        return True
    if value.startswith("file://"):
        return True
    # Reject anything that names a production home or a state db.
    lowered = value.lower()
    if "/.hermes" in lowered or "state.db" in lowered:
        return True
    return False


def is_shell_like(value: str) -> bool:
    """Return ``True`` if *value* contains shell metacharacters."""
    if not isinstance(value, str):
        return False
    return any(ch in value for ch in ("|", ";", "`", "$", ">", "<", "&", "\n", "\r"))


def sanitize_workflow_value(value: Any, *, depth: int = 0) -> Any:
    """Sanitize an arbitrary workflow input value.

    - redacts secret-looking strings
    - drops forbidden keys from dicts
    - bounds nesting depth
    - never raises; unsafe material is reduced to ``[REDACTED]`` / dropped
    """
    if depth > 6:
        return None
    if isinstance(value, str):
        return _REDACTED_VALUE if _is_secret_string(value) else value
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, val in value.items():
            if is_forbidden_input_key(key):
                continue
            out[str(key)] = sanitize_workflow_value(val, depth=depth + 1)
        return out
    if isinstance(value, list):
        return [sanitize_workflow_value(v, depth=depth + 1) for v in value]
    if isinstance(value, tuple):
        return [sanitize_workflow_value(v, depth=depth + 1) for v in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    # Reject any other type (callable, bytes, object repr, …).
    return None


def _bounded_string(value: Any, *, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if len(stripped) > max_length:
        stripped = stripped[:max_length]
    if _is_secret_string(stripped):
        return None
    return stripped


def coerce_bounded_string(value: Any, *, max_length: int) -> str | None:
    """Coerce *value* to a bounded, secret-free string. ``None`` on invalid."""
    return _bounded_string(value, max_length=max_length)


# ---------------------------------------------------------------------------
# 8. Frozen data records
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WorkflowAuditLink:
    """A safe cross-reference from a workflow step to a Phase 2D audit event.

    Only the public correlation id + kind are kept — never the raw payload.
    """

    audit_id: str
    audit_kind: str
    label: str | None = None

    def to_safe_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "auditId": self.audit_id,
            "auditKind": self.audit_kind,
        }
        if self.label is not None:
            out["label"] = self.label
        return out


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """One ordered step in a workflow plan/execution."""

    step_id: str
    step_type: str
    title: str
    status: str = STATUS_PLANNED
    description: str | None = None
    tool_id: str | None = None
    provider_mode: str | None = None
    allowed_tool_ids: tuple[str, ...] = ()
    requires_approval: bool = True
    requires_dry_run: bool = True
    requires_confirmation: bool = False
    write_required: bool = False
    read_only: bool = True
    local_side_effects: bool = False
    external_side_effects: bool = False
    input: Mapping[str, Any] = field(default_factory=dict)
    safe_input_summary: Mapping[str, Any] = field(default_factory=dict)
    preview: Mapping[str, Any] | None = None
    result: Mapping[str, Any] | None = None
    audit_links: tuple[WorkflowAuditLink, ...] = ()
    blocked_reason: str | None = None
    approval_id: str | None = None
    created_at: str = ""
    updated_at: str = ""

    def to_safe_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "stepId": self.step_id,
            "stepType": self.step_type,
            "title": self.title,
            "status": self.status,
            "requiresApproval": self.requires_approval,
            "requiresDryRun": self.requires_dry_run,
            "requiresConfirmation": self.requires_confirmation,
            "writeRequired": self.write_required,
            "readOnly": self.read_only,
            "localSideEffects": self.local_side_effects,
            "externalSideEffects": self.external_side_effects,
            "input": redact_secret_strings(dict(self.input) if self.input else {}),
            "safeInputSummary": dict(self.safe_input_summary) if self.safe_input_summary else {},
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if self.description is not None:
            data["description"] = self.description
        if self.tool_id is not None:
            data["toolId"] = self.tool_id
        if self.provider_mode is not None:
            data["providerMode"] = self.provider_mode
        if self.allowed_tool_ids:
            data["allowedToolIds"] = list(self.allowed_tool_ids)
        if self.preview is not None:
            data["preview"] = redact_secret_strings(dict(self.preview))
        if self.result is not None:
            data["result"] = redact_secret_strings(dict(self.result))
        if self.audit_links:
            data["auditLinks"] = [link.to_safe_dict() for link in self.audit_links]
        if self.blocked_reason is not None:
            data["blockedReason"] = self.blocked_reason
        if self.approval_id is not None:
            data["approvalId"] = self.approval_id
        return data


@dataclass(frozen=True, slots=True)
class WorkflowApprovalGate:
    """A human-approval gate for a single workflow step.

    The approval reuses the Phase 2C-H1 file-backed confirmation store under
    the ``workflow_step_approval`` scope. Only the public ids are kept here —
    the raw token / hash live in the confirmation store.
    """

    approval_id: str
    step_id: str
    workflow_execution_id: str
    step_digest: str
    issued_at: str
    expires_at: str
    used_at: str | None = None

    def to_safe_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "approvalId": self.approval_id,
            "stepId": self.step_id,
            "workflowExecutionId": self.workflow_execution_id,
            "issuedAt": self.issued_at,
            "expiresAt": self.expires_at,
            "used": self.used_at is not None,
        }
        if self.used_at is not None:
            out["usedAt"] = self.used_at
        return out


@dataclass(frozen=True, slots=True)
class WorkflowTimelineEvent:
    """One entry in a workflow execution's append-only timeline."""

    event_id: str
    event_type: str
    created_at: str
    step_id: str | None = None
    step_type: str | None = None
    step_status: str | None = None
    approval_id: str | None = None
    tool_id: str | None = None
    provider_mode: str | None = None
    write_preview_id: str | None = None
    rollback_id: str | None = None
    audit_links: tuple[WorkflowAuditLink, ...] = ()
    message: str | None = None
    blocked_reason: str | None = None

    def to_safe_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "eventId": self.event_id,
            "eventType": self.event_type,
            "createdAt": self.created_at,
        }
        if self.step_id is not None:
            data["stepId"] = self.step_id
        if self.step_type is not None:
            data["stepType"] = self.step_type
        if self.step_status is not None:
            data["stepStatus"] = self.step_status
        if self.approval_id is not None:
            data["approvalId"] = self.approval_id
        if self.tool_id is not None:
            data["toolId"] = self.tool_id
        if self.provider_mode is not None:
            data["providerMode"] = self.provider_mode
        if self.write_preview_id is not None:
            data["writePreviewId"] = self.write_preview_id
        if self.rollback_id is not None:
            data["rollbackId"] = self.rollback_id
        if self.audit_links:
            data["auditLinks"] = [link.to_safe_dict() for link in self.audit_links]
        if self.message is not None:
            data["message"] = self.message
        if self.blocked_reason is not None:
            data["blockedReason"] = self.blocked_reason
        return data


@dataclass(frozen=True, slots=True)
class WorkflowSafetyBoundary:
    """The frozen Phase 3A capability boundary, surfaced to the UI."""

    real_provider: str = "blocked"
    provider_auto_write: str = "blocked"
    autonomous_write: str = "blocked"
    write_execute: str = "blocked"
    rollback_execute: str = "blocked"
    shell_command: str = "blocked"
    database_mutation: str = "blocked"
    external_service_write: str = "blocked"
    production_rollout: str = "blocked"
    sandbox_write_preview: str = "allowed"
    rollback_reference: str = "allowed"
    fake_provider: str = "allowed"
    manual_approval: str = "required"
    audit: str = "enabled"

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "realProvider": self.real_provider,
            "providerAutoWrite": self.provider_auto_write,
            "autonomousWrite": self.autonomous_write,
            "writeExecute": self.write_execute,
            "rollbackExecute": self.rollback_execute,
            "shellCommand": self.shell_command,
            "databaseMutation": self.database_mutation,
            "externalServiceWrite": self.external_service_write,
            "productionRollout": self.production_rollout,
            "sandboxWritePreview": self.sandbox_write_preview,
            "rollbackReference": self.rollback_reference,
            "fakeProvider": self.fake_provider,
            "manualApproval": self.manual_approval,
            "audit": self.audit,
        }


#: The single frozen boundary instance reused across the workflow surface.
WORKFLOW_SAFETY_BOUNDARY = WorkflowSafetyBoundary()


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    """A reusable workflow definition (the plan template)."""

    workflow_id: str
    schema_version: str
    title: str
    description: str | None
    created_at: str
    updated_at: str
    created_by: str
    phase: str
    mode: str
    steps: tuple[WorkflowStep, ...]
    safety_boundary: WorkflowSafetyBoundary
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "workflowId": self.workflow_id,
            "schemaVersion": self.schema_version,
            "title": self.title,
            "description": self.description,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "createdBy": self.created_by,
            "phase": self.phase,
            "mode": self.mode,
            "steps": [step.to_safe_dict() for step in self.steps],
            "safetyBoundary": self.safety_boundary.to_safe_dict(),
            "metadata": redact_secret_strings(dict(self.metadata) if self.metadata else {}),
        }


@dataclass(frozen=True, slots=True)
class WorkflowPlan:
    """The preview of a proposed workflow plan (planner output)."""

    workflow_id: str
    workflow_plan_id: str
    schema_version: str
    title: str
    goal: str | None
    steps: tuple[WorkflowStep, ...]
    safety_boundary: WorkflowSafetyBoundary
    blocked_steps: tuple[WorkflowStep, ...]
    required_approvals: int
    audit_preview: Mapping[str, Any]
    summary: str
    created_at: str
    allowed_step_types: tuple[str, ...] = tuple(sorted(ALLOWED_STEP_TYPES))
    forbidden_step_types: tuple[str, ...] = tuple(sorted(FORBIDDEN_STEP_TYPES))

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "workflowId": self.workflow_id,
            "workflowPlanId": self.workflow_plan_id,
            "schemaVersion": self.schema_version,
            "title": self.title,
            "goal": self.goal,
            "steps": [step.to_safe_dict() for step in self.steps],
            "safetyBoundary": self.safety_boundary.to_safe_dict(),
            "blockedSteps": [step.to_safe_dict() for step in self.blocked_steps],
            "requiredApprovals": self.required_approvals,
            "auditPreview": redact_secret_strings(dict(self.audit_preview)),
            "summary": self.summary,
            "createdAt": self.created_at,
            "allowedStepTypes": list(self.allowed_step_types),
            "forbiddenStepTypes": list(self.forbidden_step_types),
        }


@dataclass(frozen=True, slots=True)
class WorkflowExecutionState:
    """The live, mutable state of one workflow execution."""

    workflow_execution_id: str
    workflow_id: str
    workflow_plan_id: str
    schema_version: str
    title: str
    status: str
    steps: tuple[WorkflowStep, ...]
    cursor_step_id: str | None
    safety_boundary: WorkflowSafetyBoundary
    created_at: str
    updated_at: str
    timeline: tuple[WorkflowTimelineEvent, ...] = ()
    completed_step_count: int = 0
    total_step_count: int = 0

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "workflowExecutionId": self.workflow_execution_id,
            "workflowId": self.workflow_id,
            "workflowPlanId": self.workflow_plan_id,
            "schemaVersion": self.schema_version,
            "title": self.title,
            "status": self.status,
            "steps": [step.to_safe_dict() for step in self.steps],
            "cursorStepId": self.cursor_step_id,
            "safetyBoundary": self.safety_boundary.to_safe_dict(),
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "timeline": [event.to_safe_dict() for event in self.timeline],
            "completedStepCount": self.completed_step_count,
            "totalStepCount": self.total_step_count,
        }


# ---------------------------------------------------------------------------
# 9. Validation helpers
# ---------------------------------------------------------------------------


def is_allowed_step_type(value: Any) -> bool:
    return isinstance(value, str) and value in ALLOWED_STEP_TYPES


def is_forbidden_step_type(value: Any) -> bool:
    return isinstance(value, str) and value in FORBIDDEN_STEP_TYPES


def is_valid_step_status(value: Any) -> bool:
    return isinstance(value, str) and value in VALID_STEP_STATUSES


def is_valid_execution_status(value: Any) -> bool:
    return isinstance(value, str) and value in VALID_EXECUTION_STATUSES


def is_valid_workflow_event_type(value: Any) -> bool:
    return isinstance(value, str) and value in VALID_WORKFLOW_EVENT_TYPES


def validate_workflow_definition(definition: WorkflowDefinition) -> tuple[bool, str | None]:
    """Validate a :class:`WorkflowDefinition` structurally."""
    if not isinstance(definition, WorkflowDefinition):
        return False, "definition is not a WorkflowDefinition"
    if definition.schema_version != WORKFLOW_SCHEMA_VERSION:
        return False, "schemaVersion is not workflow_schema_v1"
    if not is_valid_workflow_id(definition.workflow_id, WORKFLOW_ID_PREFIX):
        return False, "workflowId is malformed"
    if not definition.title or len(definition.title) > _MAX_TITLE_LENGTH:
        return False, "title is missing or too long"
    if not definition.steps:
        return False, "workflow has no steps"
    if len(definition.steps) > _MAX_STEPS:
        return False, "workflow has too many steps"
    seen_ids: set[str] = set()
    for step in definition.steps:
        if step.step_id in seen_ids:
            return False, f"duplicate step id: {step.step_id}"
        seen_ids.add(step.step_id)
        if not is_allowed_step_type(step.step_type):
            return False, f"step {step.step_id} has a non-allowed step type"
    return True, None


__all__ = [
    "WORKFLOW_SCHEMA_VERSION",
    "WORKFLOW_ID_PREFIX",
    "WORKFLOW_PLAN_ID_PREFIX",
    "WORKFLOW_STEP_ID_PREFIX",
    "WORKFLOW_EXECUTION_ID_PREFIX",
    "WORKFLOW_AUDIT_ID_PREFIX",
    "WORKFLOW_APPROVAL_ID_PREFIX",
    "WORKFLOW_PHASE",
    "WORKFLOW_AUDIT_SOURCE",
    "WORKFLOW_SAFETY_BOUNDARY",
    "ALLOWED_STEP_TYPES",
    "FORBIDDEN_STEP_TYPES",
    "FORBIDDEN_STEP_BLOCKED_REASONS",
    "VALID_STEP_STATUSES",
    "VALID_EXECUTION_STATUSES",
    "ALLOWED_PROVIDER_MODES",
    "VALID_WORKFLOW_EVENT_TYPES",
    "WORKFLOW_BLOCKED_REASONS",
    # step type constants
    "STEP_READ_ONLY_TOOL",
    "STEP_FAKE_PROVIDER_ROUNDTRIP",
    "STEP_SANDBOX_WRITE_PREVIEW",
    "STEP_ROLLBACK_REFERENCE",
    "STEP_MANUAL_NOTE",
    "STEP_AUDIT_QUERY",
    # status constants
    "STATUS_DRAFT",
    "STATUS_PLANNED",
    "STATUS_PREVIEWED",
    "STATUS_APPROVAL_REQUIRED",
    "STATUS_APPROVED",
    "STATUS_READY",
    "STATUS_RUNNING",
    "STATUS_COMPLETED",
    "STATUS_BLOCKED",
    "STATUS_FAILED",
    "STATUS_SKIPPED",
    "EXEC_STATUS_DRAFT",
    "EXEC_STATUS_RUNNING",
    "EXEC_STATUS_PAUSED",
    "EXEC_STATUS_COMPLETED",
    "EXEC_STATUS_FAILED",
    # provider modes
    "PROVIDER_MODE_DISABLED",
    "PROVIDER_MODE_FAKE",
    "PROVIDER_MODE_REAL",
    # blocked reasons
    "BLOCKED_REAL_PROVIDER",
    "BLOCKED_AUTONOMOUS_WRITE",
    "BLOCKED_PROVIDER_WRITE",
    "BLOCKED_ROLLBACK_EXECUTE",
    "BLOCKED_SHELL",
    "BLOCKED_DATABASE",
    "BLOCKED_EXTERNAL_SERVICE",
    "BLOCKED_PRODUCTION",
    "BLOCKED_PLUGIN_DYNAMIC_LOAD",
    "BLOCKED_STEP_TYPE_NOT_ALLOWED",
    "BLOCKED_APPROVAL_REQUIRED",
    "BLOCKED_APPROVAL_EXPIRED",
    "BLOCKED_APPROVAL_SCOPE_MISMATCH",
    "BLOCKED_APPROVAL_STEP_MISMATCH",
    "BLOCKED_APPROVAL_DIGEST_MISMATCH",
    "BLOCKED_APPROVAL_ALREADY_USED",
    "BLOCKED_UNSAFE_PATH",
    "BLOCKED_SECRET_INPUT",
    "BLOCKED_RAW_TOKEN_INPUT",
    "BLOCKED_INVALID_INPUT",
    "BLOCKED_STORE_UNAVAILABLE",
    # audit event types
    "EVENT_WORKFLOW_PLAN_CREATED",
    "EVENT_WORKFLOW_PLAN_BLOCKED",
    "EVENT_WORKFLOW_EXECUTION_CREATED",
    "EVENT_WORKFLOW_STEP_PREVIEW_CREATED",
    "EVENT_WORKFLOW_STEP_APPROVAL_CREATED",
    "EVENT_WORKFLOW_STEP_APPROVAL_USED",
    "EVENT_WORKFLOW_STEP_STARTED",
    "EVENT_WORKFLOW_STEP_COMPLETED",
    "EVENT_WORKFLOW_STEP_BLOCKED",
    "EVENT_WORKFLOW_STEP_FAILED",
    "EVENT_WORKFLOW_TIMELINE_UPDATED",
    "EVENT_WORKFLOW_EXECUTION_COMPLETED",
    # data classes
    "WorkflowAuditLink",
    "WorkflowStep",
    "WorkflowApprovalGate",
    "WorkflowTimelineEvent",
    "WorkflowSafetyBoundary",
    "WorkflowDefinition",
    "WorkflowPlan",
    "WorkflowExecutionState",
    # helpers
    "new_workflow_id",
    "is_valid_workflow_id",
    "is_allowed_step_type",
    "is_forbidden_step_type",
    "blocked_reason_for_step_type",
    "is_valid_step_status",
    "is_valid_execution_status",
    "is_valid_workflow_event_type",
    "validate_workflow_definition",
    "redact_secret_strings",
    "contains_secret_material",
    "sanitize_workflow_value",
    "is_forbidden_input_key",
    "contains_unsafe_path",
    "is_shell_like",
    "coerce_bounded_string",
]
