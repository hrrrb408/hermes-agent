"""Phase 3C Capability Registry — Audit Bridge.

Writes dev-only ``capability_registry_*`` breadcrumb events into the existing
Phase 2D durable audit store. This module does **not** introduce a new audit
kind: registry events reuse ``AUDIT_KIND_INTERNAL`` with
``eventType=capability_registry_*`` so they are discoverable by the existing
audit viewer / query engine without any new audit-writer surface (mirroring the
Phase 3A workflow-audit bridge).

Design constraints (frozen):

  - stdlib only (besides the existing dev audit store, which is stdlib only)
  - every event is sanitized by the unified store sanitizer before append, and
    this bridge applies its own defensive re-redaction before building the
    event — a defective caller can never leak a forbidden field
  - safe fields only: ``capabilityId`` / ``category`` / ``permissionClass`` /
    ``trustLevel`` / ``status`` / ``blockedReason`` / ``requiresApproval`` /
    ``requiresAudit`` / ``devOnly`` / ``productionAllowed`` / ``routeExposure``
    / value-free ``safeMetadata``
  - forbidden fields never reach the store: API key, Authorization, Bearer
    token, raw secret, raw prompt/response, full tokenHash, callable repr,
    shell command, SQL statement, production path, local plugin path, dynamic
    import path
  - the write is confined to the dev ``HERMES_HOME``; never ``~/.hermes``
  - the write is best-effort: a failure is reported in the result and never
    raises (callers fail safe — a missing audit id means "no link", not
    "abort"), **and** audit failure never enables a capability

Phase: 3C — Static dev-only Capability Registry
Status: implemented
"""

from __future__ import annotations

from typing import Any, Mapping

from hermes_cli.dev_web_audit_schema import AUDIT_KIND_INTERNAL, AUDIT_SCHEMA_VERSION
from hermes_cli.dev_web_audit_store import (
    AuditStoreWriteResult,
    append_audit_event,
    build_audit_event,
)

#: Audit source label for capability-registry breadcrumbs.
CAPABILITY_REGISTRY_AUDIT_SOURCE = "dev_web_capability_registry"
#: Audit phase label.
CAPABILITY_REGISTRY_PHASE = "phase-3c"

#: The frozen set of ``capability_registry_*`` event types this bridge emits.
CAPABILITY_REGISTRY_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "capability_registry_loaded",
        "capability_registry_validation_passed",
        "capability_registry_validation_failed",
        "capability_registry_capability_viewed",
        "capability_registry_capability_blocked",
        "capability_registry_permission_classified",
        "capability_registry_trust_classified",
        "capability_registry_manifest_rejected",
        "capability_registry_route_governance_checked",
        "capability_registry_no_dynamic_loading_checked",
    }
)

#: Fields a ``capability_registry_*`` event payload may carry (the safe set).
SAFE_PAYLOAD_FIELDS: frozenset[str] = frozenset(
    {
        "capabilityId",
        "category",
        "permissionClass",
        "trustLevel",
        "status",
        "blockedReason",
        "requiresApproval",
        "requiresAudit",
        "devOnly",
        "productionAllowed",
        "routeExposure",
        "safeMetadata",
    }
)


def redact_capability_registry_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a safe, shallow copy of a capability-registry audit payload.

    Keeps **only** the frozen safe fields, coerces non-JSON values safely, and
    bounds strings. Never raises. A second defensive re-redaction runs at the
    store layer (``sanitize_audit_event``) before append.
    """
    if not isinstance(payload, Mapping):
        return {}
    cleaned: dict[str, Any] = {}
    for key in SAFE_PAYLOAD_FIELDS:
        if key not in payload:
            continue
        value = payload[key]
        # Coerce non-JSON-native values safely (no str() on arbitrary objects).
        if isinstance(value, bool):
            cleaned[key] = value
        elif isinstance(value, (int, float)):
            cleaned[key] = value
        elif isinstance(value, str):
            cleaned[key] = value
        elif isinstance(value, Mapping):
            cleaned[key] = redact_capability_registry_payload(value)
        elif isinstance(value, (list, tuple)):
            cleaned[key] = [
                redact_capability_registry_payload(v) if isinstance(v, Mapping) else v
                for v in value
                if isinstance(v, (bool, int, float, str))
            ]
        else:
            # bytes / callables / arbitrary objects → drop the value entirely.
            continue
    cleaned["redactionApplied"] = True
    return cleaned


def write_capability_registry_audit(
    *,
    event_type: str,
    capability_id: str | None = None,
    category: str | None = None,
    permission_class: str | None = None,
    trust_level: str | None = None,
    status: str | None = None,
    blocked_reason: str | None = None,
    requires_approval: bool | None = None,
    requires_audit: bool | None = None,
    dev_only: bool | None = None,
    production_allowed: bool | None = None,
    route_exposure: str | None = None,
    safe_metadata: Mapping[str, Any] | None = None,
    hermes_home: str | None = None,
) -> AuditStoreWriteResult:
    """Append one ``capability_registry_*`` breadcrumb event to the durable store.

    Returns the :class:`AuditStoreWriteResult`. The ``event_id`` (on success)
    is the correlation id the caller may surface as an audit link. Never raises;
    a store failure is reported in the result and never enables a capability.
    """
    if event_type not in CAPABILITY_REGISTRY_EVENT_TYPES:
        # Unknown event types are normalized to the load breadcrumb so a caller
        # bug can never produce an un-queryable event.
        event_type = "capability_registry_loaded"

    payload = redact_capability_registry_payload(
        {
            "capabilityId": capability_id,
            "category": category,
            "permissionClass": permission_class,
            "trustLevel": trust_level,
            "status": status,
            "blockedReason": blocked_reason,
            "requiresApproval": requires_approval,
            "requiresAudit": requires_audit,
            "devOnly": dev_only,
            "productionAllowed": production_allowed,
            "routeExposure": route_exposure,
            "safeMetadata": redact_capability_registry_payload(safe_metadata) if safe_metadata else None,
        }
    )

    summary: dict[str, Any] = {
        "schemaOrigin": "capability_registry_audit_v1",
        "eventType": event_type,
        "redactionApplied": True,
    }
    # Surface the safe payload into summary (sanitized again by the store).
    for key, value in payload.items():
        if value is not None:
            summary[key] = value

    meta: dict[str, Any] = {
        "schemaOrigin": "capability_registry_audit_v1",
        "registryPhase": CAPABILITY_REGISTRY_PHASE,
    }

    event = build_audit_event(
        event_type=event_type,
        audit_kind=AUDIT_KIND_INTERNAL,
        source=CAPABILITY_REGISTRY_AUDIT_SOURCE,
        status=status,
        blocked_reason=blocked_reason,
        read_only=True,
        write_required=False,
        external_network_called=False,
        local_side_effects=False,
        external_side_effects=False,
        redaction_applied=True,
        summary=summary,
        safe_metadata=meta,
    )
    event["schemaVersion"] = AUDIT_SCHEMA_VERSION
    try:
        return append_audit_event(event, hermes_home=hermes_home)
    except Exception:
        # Fail safe: never propagate a store error to the registry caller.
        # Audit failure must NEVER enable a capability.
        return AuditStoreWriteResult(
            written=False,
            event_id=None,
            sequence=None,
            segment=None,
            rotated=False,
            error_code="capability_registry_audit_write_failed",
            error_message="Capability registry audit write failed.",
        )


__all__ = [
    "CAPABILITY_REGISTRY_AUDIT_SOURCE",
    "CAPABILITY_REGISTRY_PHASE",
    "CAPABILITY_REGISTRY_EVENT_TYPES",
    "SAFE_PAYLOAD_FIELDS",
    "redact_capability_registry_payload",
    "write_capability_registry_audit",
]
