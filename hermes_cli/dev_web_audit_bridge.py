"""Legacy → Canonical Audit Bridge for the Hermes Dev WebUI (Phase 2D).

Maps the existing per-writer legacy audit events (dry-run, pre/post execution,
provider, write, rollback, confirmation) into canonical ``audit_schema_v2``
events and appends them to the durable audit store.

This is the **dual-write** integration layer. Every call is best-effort:
  - it NEVER raises (the legacy write has already succeeded and is the source
    of truth for backward compatibility)
  - it NEVER changes a legacy writer's return value
  - a store-write failure is logged only in the result and silently dropped

Hard guarantees:
  - the canonical event is sanitized by the unified sanitizer before append
  - no raw arguments, secrets, full token hashes, callable reprs, or
    production paths ever reach the store
  - the store write is confined to the dev ``HERMES_HOME``

Phase: 2D — Durable Dev Audit Store MVP
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from hermes_cli.dev_web_audit_schema import (
    AUDIT_SCHEMA_VERSION,
    AUDIT_KIND_CONFIRMATION,
    AUDIT_KIND_DRY_RUN,
    AUDIT_KIND_POST_EXECUTION,
    AUDIT_KIND_PRE_EXECUTION,
    AUDIT_KIND_PROVIDER,
    AUDIT_KIND_ROLLBACK,
    AUDIT_KIND_WRITE,
)
from hermes_cli.dev_web_audit_store import (
    AuditStoreWriteResult,
    append_audit_event,
    build_audit_event,
)


# ---------------------------------------------------------------------------
# 1. Legacy → canonical mappers
# ---------------------------------------------------------------------------


def _coerce_str(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def map_dry_run_event(legacy: Mapping[str, Any]) -> dict[str, Any]:
    """Map a dry-run audit event to a canonical event."""
    event_id = _coerce_str(legacy.get("eventId")) or str(uuid.uuid4())
    decision = _coerce_str(legacy.get("decision"))
    status = "preview"
    if decision == "would_allow":
        status = "ok"
    elif decision in ("would_block", "blocked"):
        status = "blocked"
    return build_audit_event(
        event_type=_coerce_str(legacy.get("eventType")) or "tool_dry_run",
        audit_kind=AUDIT_KIND_DRY_RUN,
        source="dry_run_api",
        tool_id=_coerce_str(legacy.get("canonicalName")),
        status=status,
        redaction_applied=bool(legacy.get("redactionApplied")),
        readOnly=True,
        writeRequired=False,
        eventId=event_id,
        dryRunId=_coerce_str(legacy.get("eventId")),
        summary={
            "decision": decision,
            "riskTier": legacy.get("riskTier"),
            "toolExists": bool(legacy.get("toolExists")),
        },
        safeMetadata={
            "requestId": legacy.get("requestId"),
            "durationMs": legacy.get("durationMs"),
        },
    )


def map_pre_execution_event(legacy: Mapping[str, Any]) -> dict[str, Any]:
    """Map a pre-execution audit event to a canonical event."""
    pe_id = _coerce_str(legacy.get("preExecutionAuditId")) or str(uuid.uuid4())
    return build_audit_event(
        event_type="pre_execution_audit",
        audit_kind=AUDIT_KIND_PRE_EXECUTION,
        source="execute_api",
        tool_id=_coerce_str(legacy.get("canonicalName")),
        status="ok",
        readOnly=True,
        writeRequired=False,
        eventId=pe_id,
        executionId=_coerce_str(legacy.get("executeRequestId")),
        preExecutionAuditId=_coerce_str(legacy.get("preExecutionAuditId")),
        dryRunId=_coerce_str(legacy.get("dryRunRequestId")),
        summary={
            "riskTier": legacy.get("riskTier"),
            "policyVersion": legacy.get("policyVersion"),
        },
        safeMetadata={},
    )


def map_post_execution_event(legacy: Mapping[str, Any]) -> dict[str, Any]:
    """Map a post-execution audit event to a canonical event."""
    pex_id = _coerce_str(legacy.get("postExecutionAuditId")) or str(uuid.uuid4())
    side = legacy.get("sideEffectFlags") if isinstance(legacy.get("sideEffectFlags"), dict) else {}
    result_summary = legacy.get("resultSummary") if isinstance(legacy.get("resultSummary"), dict) else {}
    status = _coerce_str(legacy.get("executionStatus")) or "completed"
    return build_audit_event(
        event_type=_coerce_str(legacy.get("eventType")) or "post_execution_audit",
        audit_kind=AUDIT_KIND_POST_EXECUTION,
        source="execute_api",
        tool_id=_coerce_str(legacy.get("canonicalName")),
        status=status,
        readOnly=True,
        writeRequired=False,
        providerSchemaSent=_to_bool(side.get("providerSchemaSent")),
        providerApiCalled=_to_bool(side.get("providerApiCalled")),
        externalSideEffects=_to_bool(side.get("externalSideEffects")),
        eventId=pex_id,
        executionId=_coerce_str(legacy.get("executeRequestId")),
        preExecutionAuditId=_coerce_str(legacy.get("preExecutionAuditId")),
        handlerCallId=_coerce_str(legacy.get("handlerCallId")),
        dispatchId=_coerce_str(legacy.get("dispatchId")),
        postExecutionAuditId=_coerce_str(legacy.get("postExecutionAuditId")),
        summary={
            "toolResultType": result_summary.get("toolResultType"),
            "messageLength": result_summary.get("messageLength"),
            "questionCount": result_summary.get("questionCount"),
            "resultSizeBytes": result_summary.get("resultSizeBytes"),
        },
        safeMetadata={},
    )


def map_provider_event(legacy: Mapping[str, Any]) -> dict[str, Any]:
    """Map a provider audit event to a canonical event."""
    event_id = _coerce_str(legacy.get("eventId")) or str(uuid.uuid4())
    event_type = _coerce_str(legacy.get("eventType")) or "provider_audit"
    provider_mode = _coerce_str(legacy.get("providerMode")) or "fake"
    return build_audit_event(
        event_type=event_type,
        audit_kind=AUDIT_KIND_PROVIDER,
        source="provider_api",
        status=_coerce_str(legacy.get("status")) or "ok",
        providerMode=provider_mode,
        providerSchemaSent=_to_bool(legacy.get("providerSchemaSent")),
        providerApiCalled=_to_bool(legacy.get("providerApiCalled")),
        externalNetworkCalled=_to_bool(legacy.get("externalNetworkCalled")),
        externalSideEffects=_to_bool(legacy.get("externalSideEffects")),
        readOnly=True,
        writeRequired=False,
        eventId=event_id,
        providerRequestId=_coerce_str(legacy.get("providerRequestId")),
        providerResponseId=_coerce_str(legacy.get("providerResponseId")),
        summary={
            "providerMode": provider_mode,
            "roundtripId": legacy.get("roundtripId"),
        },
        safeMetadata={},
    )


def map_write_event(legacy: Mapping[str, Any]) -> dict[str, Any]:
    """Map a controlled-write audit event to a canonical event."""
    event_id = _coerce_str(legacy.get("eventId")) or str(uuid.uuid4())
    status = _coerce_str(legacy.get("status")) or "preview"
    return build_audit_event(
        event_type=_coerce_str(legacy.get("eventType")) or "write_audit",
        audit_kind=AUDIT_KIND_WRITE,
        source="write_api",
        tool_id=_coerce_str(legacy.get("toolId")),
        status=status,
        blockedReason=_coerce_str(legacy.get("blockedReason")),
        readOnly=False,
        writeRequired=True,
        localSideEffects=True,
        externalSideEffects=False,
        # Write audits always exclude raw file content / raw arguments by
        # construction (the bridge never carries them), so redaction is
        # always effectively applied to this audit kind.
        redaction_applied=True,
        eventId=event_id,
        writePlanId=_coerce_str(legacy.get("writePlanId")),
        writePreviewId=_coerce_str(legacy.get("writePreviewId")),
        rollbackId=_coerce_str(legacy.get("rollbackId")),
        confirmationTokenId=_coerce_str(legacy.get("confirmationTokenId")),
        summary={
            "operation": legacy.get("operation"),
            "targetRelativePath": legacy.get("targetRelativePath"),
            "status": status,
        },
        safeMetadata={},
    )


def map_rollback_event(legacy: Mapping[str, Any]) -> dict[str, Any]:
    """Map a rollback audit/manifest event to a canonical event."""
    event_id = _coerce_str(legacy.get("eventId")) or str(uuid.uuid4())
    return build_audit_event(
        event_type=_coerce_str(legacy.get("eventType")) or "rollback_audit",
        audit_kind=AUDIT_KIND_ROLLBACK,
        source="rollback_api",
        tool_id=_coerce_str(legacy.get("toolId")),
        status=_coerce_str(legacy.get("status")) or "completed",
        readOnly=False,
        writeRequired=True,
        localSideEffects=True,
        externalSideEffects=False,
        redaction_applied=True,
        eventId=event_id,
        rollbackId=_coerce_str(legacy.get("rollbackId")),
        writePlanId=_coerce_str(legacy.get("writePlanId")),
        confirmationTokenId=_coerce_str(legacy.get("confirmationTokenId")),
        summary={
            "rollbackId": legacy.get("rollbackId"),
            "executedSteps": legacy.get("executedSteps"),
            "status": legacy.get("status"),
        },
        safeMetadata={},
    )


def map_confirmation_event(legacy: Mapping[str, Any]) -> dict[str, Any]:
    """Map a confirmation-token audit event to a canonical event."""
    token_id = _coerce_str(legacy.get("tokenId")) or _coerce_str(legacy.get("eventId")) or str(uuid.uuid4())
    return build_audit_event(
        event_type=_coerce_str(legacy.get("eventType")) or "confirmation_token_audit",
        audit_kind=AUDIT_KIND_CONFIRMATION,
        source="confirmation",
        tool_id=_coerce_str(legacy.get("toolId")),
        status=_coerce_str(legacy.get("status")) or "ok",
        readOnly=False,
        writeRequired=True,
        redaction_applied=True,
        eventId=token_id,
        confirmationTokenId=token_id,
        writePlanId=_coerce_str(legacy.get("writePlanId")),
        summary={
            "tokenId": token_id,
            "status": legacy.get("status"),
            "used": bool(legacy.get("used")),
            "expired": bool(legacy.get("expired")),
        },
        safeMetadata={},
    )


_MAPPERS = {
    AUDIT_KIND_DRY_RUN: map_dry_run_event,
    AUDIT_KIND_PRE_EXECUTION: map_pre_execution_event,
    AUDIT_KIND_POST_EXECUTION: map_post_execution_event,
    AUDIT_KIND_PROVIDER: map_provider_event,
    AUDIT_KIND_WRITE: map_write_event,
    AUDIT_KIND_ROLLBACK: map_rollback_event,
    AUDIT_KIND_CONFIRMATION: map_confirmation_event,
}


# ---------------------------------------------------------------------------
# 2. Public dual-write entry point
# ---------------------------------------------------------------------------


def bridge_legacy_audit_to_store(
    legacy_event: Mapping[str, Any] | None,
    *,
    audit_kind: str,
    hermes_home: str | None = None,
) -> AuditStoreWriteResult | None:
    """Best-effort dual-write of a legacy audit event to the durable store.

    Returns the :class:`AuditStoreWriteResult` on success, or ``None`` if the
    mapping or store write was skipped/failed. **Never raises.**
    """
    try:
        if legacy_event is None or not isinstance(legacy_event, Mapping):
            return None
        mapper = _MAPPERS.get(audit_kind)
        if mapper is None:
            return None
        canonical = mapper(legacy_event)
        canonical["schemaVersion"] = AUDIT_SCHEMA_VERSION
        return append_audit_event(canonical, hermes_home=hermes_home)
    except Exception:
        # Dual-write is purely best-effort. The legacy writer has already
        # succeeded; a store failure must never propagate.
        return None


def bridge_legacy_audits_to_store(
    legacy_events: list[Mapping[str, Any]],
    *,
    audit_kind: str,
    hermes_home: str | None = None,
) -> int:
    """Batch dual-write helper. Returns the number of events written."""
    written = 0
    for legacy in legacy_events:
        result = bridge_legacy_audit_to_store(
            legacy, audit_kind=audit_kind, hermes_home=hermes_home
        )
        if result is not None and result.written:
            written += 1
    return written
