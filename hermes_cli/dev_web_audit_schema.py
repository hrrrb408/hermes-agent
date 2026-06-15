"""Canonical Audit Event Schema for the Hermes Dev WebUI (Phase 2D).

This module defines the **canonical** audit event used by the dev-only durable
audit store. Every audit writer (dry-run, pre/post execution, provider, write,
rollback, confirmation) is normalized into this single shape before it is
appended to the durable store.

Design constraints (frozen for Phase 2D):
  - stdlib only (no third-party imports)
  - no provider / handler / dispatch / agent runtime imports
  - no network IO, no file IO, no state mutation
  - all public data structures are JSON-native
  - never references ``~/.hermes`` or production ``state.db``
  - never holds raw arguments, raw tokens, full token hashes, secrets,
    callable objects, or function reprs — those are removed by the unified
    sanitizer (``dev_web_audit_sanitizer``) before any field is set

Phase: 2D — Durable Dev Audit Store MVP
Schema version: ``audit_schema_v2``
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# 1. Schema version
# ---------------------------------------------------------------------------

#: Canonical schema version tag for every durable audit event.
AUDIT_SCHEMA_VERSION = "audit_schema_v2"

# ---------------------------------------------------------------------------
# 2. Enumerations (plain string constants — JSON-native)
# ---------------------------------------------------------------------------

# auditKind — the broad category of audit event. Maps 1:1 to the legacy
# per-kind JSONL files so legacy readers and the new store stay consistent.
AUDIT_KIND_DRY_RUN = "dry_run"
AUDIT_KIND_PRE_EXECUTION = "pre_execution"
AUDIT_KIND_POST_EXECUTION = "post_execution"
AUDIT_KIND_WRITE = "write"
AUDIT_KIND_PROVIDER = "provider"
AUDIT_KIND_ROLLBACK = "rollback"
AUDIT_KIND_CONFIRMATION = "confirmation"
AUDIT_KIND_INTERNAL = "internal"

VALID_AUDIT_KINDS: frozenset[str] = frozenset(
    {
        AUDIT_KIND_DRY_RUN,
        AUDIT_KIND_PRE_EXECUTION,
        AUDIT_KIND_POST_EXECUTION,
        AUDIT_KIND_WRITE,
        AUDIT_KIND_PROVIDER,
        AUDIT_KIND_ROLLBACK,
        AUDIT_KIND_CONFIRMATION,
        AUDIT_KIND_INTERNAL,
    }
)

# source — which surface produced the event.
SOURCE_DRY_RUN_API = "dry_run_api"
SOURCE_EXECUTE_API = "execute_api"
SOURCE_PROVIDER_API = "provider_api"
SOURCE_WRITE_API = "write_api"
SOURCE_ROLLBACK_API = "rollback_api"
SOURCE_CONFIRMATION = "confirmation"
SOURCE_INTERNAL = "internal"

VALID_SOURCES: frozenset[str] = frozenset(
    {
        SOURCE_DRY_RUN_API,
        SOURCE_EXECUTE_API,
        SOURCE_PROVIDER_API,
        SOURCE_WRITE_API,
        SOURCE_ROLLBACK_API,
        SOURCE_CONFIRMATION,
        SOURCE_INTERNAL,
    }
)

# status — outcome of the audited operation.
STATUS_OK = "ok"
STATUS_BLOCKED = "blocked"
STATUS_ERROR = "error"
STATUS_PREVIEW = "preview"
STATUS_COMPLETED = "completed"

VALID_STATUSES: frozenset[str] = frozenset(
    {STATUS_OK, STATUS_BLOCKED, STATUS_ERROR, STATUS_PREVIEW, STATUS_COMPLETED}
)

# providerMode — mirrors the provider capability modes from Phase 2B/2C.
PROVIDER_MODE_DISABLED = "disabled"
PROVIDER_MODE_FAKE = "fake"
PROVIDER_MODE_REAL = "real"

VALID_PROVIDER_MODES: frozenset[str] = frozenset(
    {PROVIDER_MODE_DISABLED, PROVIDER_MODE_FAKE, PROVIDER_MODE_REAL}
)

# mode — the execution mode the dev environment is operating under.
MODE_READ_ONLY = "read_only"
MODE_WRITE_PREVIEW = "write_preview"

VALID_MODES: frozenset[str] = frozenset({MODE_READ_ONLY, MODE_WRITE_PREVIEW})

# ---------------------------------------------------------------------------
# 3. Required canonical fields
# ---------------------------------------------------------------------------

#: Fields that MUST be present on every canonical audit event. The store
#: writer rejects (quarantines) any event missing one of these.
REQUIRED_EVENT_FIELDS: tuple[str, ...] = (
    "eventId",
    "sequence",
    "createdAt",
    "eventType",
    "auditKind",
    "schemaVersion",
)

#: The full ordered canonical field set. Every field is optional except the
#: required ones above; absent optional fields default to ``None`` / ``False``.
CANONICAL_FIELDS: tuple[str, ...] = (
    # identity
    "eventId",
    "sequence",
    "createdAt",
    "schemaVersion",
    # classification
    "eventType",
    "auditKind",
    "source",
    "phase",
    "toolId",
    "toolCategory",
    "mode",
    "status",
    "blockedReason",
    # capability / side-effect flags (all JSON-native booleans)
    "readOnly",
    "writeRequired",
    "providerMode",
    "providerSchemaSent",
    "providerApiCalled",
    "externalNetworkCalled",
    "localSideEffects",
    "externalSideEffects",
    "redactionApplied",
    # correlation ids
    "executionId",
    "dryRunId",
    "dispatchId",
    "handlerCallId",
    "preExecutionAuditId",
    "postExecutionAuditId",
    "providerRequestId",
    "providerResponseId",
    "writePlanId",
    "writePreviewId",
    "rollbackId",
    "confirmationTokenId",
    # safe payload (summary + sanitized metadata)
    "summary",
    "safeMetadata",
)

# Fields that must always serialize as a JSON boolean (default False).
BOOLEAN_FIELDS: frozenset[str] = frozenset(
    {
        "readOnly",
        "writeRequired",
        "providerSchemaSent",
        "providerApiCalled",
        "externalNetworkCalled",
        "localSideEffects",
        "externalSideEffects",
        "redactionApplied",
    }
)

# Fields that must serialize as a JSON string (or None).
STRING_FIELDS: frozenset[str] = frozenset(
    {
        "eventId",
        "createdAt",
        "schemaVersion",
        "eventType",
        "auditKind",
        "source",
        "phase",
        "toolId",
        "toolCategory",
        "mode",
        "status",
        "blockedReason",
        "providerMode",
        "executionId",
        "dryRunId",
        "dispatchId",
        "handlerCallId",
        "preExecutionAuditId",
        "postExecutionAuditId",
        "providerRequestId",
        "providerResponseId",
        "writePlanId",
        "writePreviewId",
        "rollbackId",
        "confirmationTokenId",
    }
)

# Fields that must serialize as a JSON integer (or None).
INTEGER_FIELDS: frozenset[str] = frozenset({"sequence"})

# Free-form safe payload containers (dict / list of JSON-native values).
OBJECT_FIELDS: frozenset[str] = frozenset({"summary", "safeMetadata"})

# Maximum length for any single string scalar in a canonical event. The
# sanitizer truncates before this is reached, but the schema enforces it as a
# final hard cap during validation.
MAX_SCALAR_LENGTH = 1024

# Maximum byte size of a single canonical event line (defense-in-depth cap).
MAX_EVENT_BYTES = 64 * 1024  # 64 KiB

# Match a canonical createdAt (ISO-8601 with timezone offset). We accept the
# common forms; the sanitizer stamps ``createdAt`` itself so this is only a
# defensive validation for externally-supplied timestamps.
_ISO_8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})$"
)


# ---------------------------------------------------------------------------
# 4. Canonical event dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Immutable canonical audit event.

    Instances are JSON-native by construction: every field is a primitive
    (``str`` / ``int`` / ``bool`` / ``None``) or a JSON-native container
    (``dict`` / ``list``). No callable, bytes, exception, or arbitrary object
    is ever stored.
    """

    event_id: str
    sequence: int
    created_at: str
    event_type: str
    audit_kind: str
    schema_version: str = AUDIT_SCHEMA_VERSION
    source: str | None = None
    phase: str | None = None
    tool_id: str | None = None
    tool_category: str | None = None
    mode: str | None = None
    status: str | None = None
    blocked_reason: str | None = None
    read_only: bool | None = None
    write_required: bool | None = None
    provider_mode: str | None = None
    provider_schema_sent: bool | None = None
    provider_api_called: bool | None = None
    external_network_called: bool | None = None
    local_side_effects: bool | None = None
    external_side_effects: bool | None = None
    redaction_applied: bool | None = None
    execution_id: str | None = None
    dry_run_id: str | None = None
    dispatch_id: str | None = None
    handler_call_id: str | None = None
    pre_execution_audit_id: str | None = None
    post_execution_audit_id: str | None = None
    provider_request_id: str | None = None
    provider_response_id: str | None = None
    write_plan_id: str | None = None
    write_preview_id: str | None = None
    rollback_id: str | None = None
    confirmation_token_id: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)
    safe_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the canonical camelCase JSON dict stored on disk.

        Only non-``None`` scalar/flag fields are emitted; the two safe
        containers are always emitted (possibly empty) so consumers can rely
        on their presence.
        """
        out: dict[str, Any] = {
            "eventId": self.event_id,
            "sequence": self.sequence,
            "createdAt": self.created_at,
            "eventType": self.event_type,
            "auditKind": self.audit_kind,
            "schemaVersion": self.schema_version,
            "summary": dict(self.summary) if self.summary else {},
            "safeMetadata": dict(self.safe_metadata) if self.safe_metadata else {},
        }
        # Optional scalar / flag fields — emit only when set.
        optional: dict[str, Any] = {
            "source": self.source,
            "phase": self.phase,
            "toolId": self.tool_id,
            "toolCategory": self.tool_category,
            "mode": self.mode,
            "status": self.status,
            "blockedReason": self.blocked_reason,
            "readOnly": self.read_only,
            "writeRequired": self.write_required,
            "providerMode": self.provider_mode,
            "providerSchemaSent": self.provider_schema_sent,
            "providerApiCalled": self.provider_api_called,
            "externalNetworkCalled": self.external_network_called,
            "localSideEffects": self.local_side_effects,
            "externalSideEffects": self.external_side_effects,
            "redactionApplied": self.redaction_applied,
            "executionId": self.execution_id,
            "dryRunId": self.dry_run_id,
            "dispatchId": self.dispatch_id,
            "handlerCallId": self.handler_call_id,
            "preExecutionAuditId": self.pre_execution_audit_id,
            "postExecutionAuditId": self.post_execution_audit_id,
            "providerRequestId": self.provider_request_id,
            "providerResponseId": self.provider_response_id,
            "writePlanId": self.write_plan_id,
            "writePreviewId": self.write_preview_id,
            "rollbackId": self.rollback_id,
            "confirmationTokenId": self.confirmation_token_id,
        }
        for key, value in optional.items():
            if value is not None:
                out[key] = value
        return out


@dataclass(frozen=True, slots=True)
class AuditEventEnvelope:
    """Envelope wrapping a batch of canonical events for append.

    Carries the sanitized events plus bookkeeping the store writer needs
    (schema version, event count) without leaking any internal path or lock
    state.
    """

    events: tuple[AuditEvent, ...]
    schema_version: str = AUDIT_SCHEMA_VERSION

    def to_dicts(self) -> tuple[dict[str, Any], ...]:
        return tuple(e.to_dict() for e in self.events)


# ---------------------------------------------------------------------------
# 5. Validation helpers
# ---------------------------------------------------------------------------


def is_valid_audit_kind(value: Any) -> bool:
    """Return ``True`` if *value* is a known audit kind string."""
    return isinstance(value, str) and value in VALID_AUDIT_KINDS


def is_valid_created_at(value: Any) -> bool:
    """Return ``True`` if *value* looks like an ISO-8601 timestamp."""
    return isinstance(value, str) and bool(_ISO_8601_RE.match(value))


def validate_canonical_event(event: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate that *event* is a well-formed canonical audit event dict.

    Returns ``(ok, reason)``. ``reason`` is a short, safe diagnostic string
    (never contains secret material — it only names the failing field).
    """
    if not isinstance(event, dict):
        return False, "event is not a JSON object"

    for required in REQUIRED_EVENT_FIELDS:
        if required not in event or event[required] is None:
            return False, f"missing required field: {required}"

    if event.get("schemaVersion") != AUDIT_SCHEMA_VERSION:
        return False, "schemaVersion is not audit_schema_v2"

    seq = event.get("sequence")
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 0:
        return False, "sequence must be a non-negative integer"

    if not is_valid_audit_kind(event.get("auditKind")):
        return False, "auditKind is not a known kind"

    if not isinstance(event.get("eventId"), str) or not event["eventId"]:
        return False, "eventId must be a non-empty string"

    if not isinstance(event.get("eventType"), str) or not event["eventType"]:
        return False, "eventType must be a non-empty string"

    if not is_valid_created_at(event.get("createdAt")):
        return False, "createdAt must be an ISO-8601 timestamp"

    # Type-check the optional scalar/flag fields if present.
    for key in BOOLEAN_FIELDS:
        if key in event and event[key] is not None:
            if not isinstance(event[key], bool):
                return False, f"{key} must be a boolean"

    for key in STRING_FIELDS:
        if key in event and event[key] is not None:
            if not isinstance(event[key], str):
                return False, f"{key} must be a string"
            if len(event[key]) > MAX_SCALAR_LENGTH:
                return False, f"{key} exceeds maximum length"

    for key in OBJECT_FIELDS:
        if key in event and event[key] is not None:
            if not isinstance(event[key], dict):
                return False, f"{key} must be a JSON object"

    return True, None


def required_fields() -> tuple[str, ...]:
    """Return the tuple of required canonical field names."""
    return REQUIRED_EVENT_FIELDS
