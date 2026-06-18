"""Phase 3D Plugin Descriptor Registry — Audit Bridge.

Writes dev-only ``plugin_descriptor_*`` breadcrumb events into the existing
Phase 2D durable audit store. This module does **not** introduce a new audit
kind: registry events reuse ``AUDIT_KIND_INTERNAL`` with
``eventType=plugin_descriptor_*`` so they are discoverable by the existing
audit viewer / query engine without any new audit-writer surface (mirroring the
Phase 3C capability-registry audit bridge).

Design constraints (frozen):

  - stdlib only (besides the existing dev audit store, which is stdlib only)
  - every event is sanitized by the unified store sanitizer before append, and
    this bridge applies its own defensive re-redaction before building the
    event — a defective caller can never leak a forbidden field
  - safe fields only: ``pluginId`` / ``capabilityId`` / ``permissionClass`` /
    ``trustLevel`` / ``status`` / ``blockedReason`` / ``devOnly`` /
    ``productionAllowed`` / ``requiresApproval`` / ``requiresAudit`` /
    value-free ``safeMetadata``
  - forbidden fields never reach the store: API key, Authorization, Bearer
    token, raw secret, raw prompt/response, full tokenHash, callable repr,
    shell command, SQL statement, production path, local plugin path, dynamic
    import path, external URL, download URL, install command
  - the write is confined to the dev ``HERMES_HOME``; never ``~/.hermes``
  - the write is best-effort: a failure is reported in the result and never
    raises, **and** audit failure never enables a descriptor / grants
    permission / creates an execution path

Note: ``plugin_descriptor_execution_requested`` / ``plugin_descriptor_execution_blocked``
exist **only** to record that an execution request was intercepted. They never
perform an execution. A descriptor registry has no plugin runtime, so any
"execution request" is blocked by construction.

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
Status: implemented. No plugin runtime execution.
"""

from __future__ import annotations

from typing import Any, Mapping

from hermes_cli.dev_web_audit_schema import AUDIT_KIND_INTERNAL, AUDIT_SCHEMA_VERSION
from hermes_cli.dev_web_audit_store import (
    AuditStoreWriteResult,
    append_audit_event,
    build_audit_event,
)

#: Audit source label for plugin-descriptor-registry breadcrumbs.
PLUGIN_DESCRIPTOR_AUDIT_SOURCE = "dev_web_plugin_descriptor_registry"
#: Audit phase label.
PLUGIN_DESCRIPTOR_PHASE = "phase-3d"

#: The frozen set of ``plugin_descriptor_*`` event types this bridge emits.
#: ``plugin_descriptor_execution_requested`` / ``plugin_descriptor_execution_blocked``
#: record that an execution request was intercepted — they never execute.
PLUGIN_DESCRIPTOR_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "plugin_descriptor_registry_loaded",
        "plugin_descriptor_validation_passed",
        "plugin_descriptor_validation_failed",
        "plugin_descriptor_rejected",
        "plugin_descriptor_blocked",
        "plugin_descriptor_capability_binding_checked",
        "plugin_descriptor_permission_classified",
        "plugin_descriptor_trust_classified",
        "plugin_descriptor_visibility_rendered",
        "plugin_descriptor_execution_requested",
        "plugin_descriptor_execution_blocked",
        "plugin_runtime_disabled",
        "plugin_no_dynamic_loading_checked",
        "plugin_route_governance_checked",
    }
)

#: Fields a ``plugin_descriptor_*`` event payload may carry (the safe set).
SAFE_PAYLOAD_FIELDS: frozenset[str] = frozenset(
    {
        "pluginId",
        "capabilityId",
        "permissionClass",
        "trustLevel",
        "status",
        "blockedReason",
        "devOnly",
        "productionAllowed",
        "requiresApproval",
        "requiresAudit",
        "redactionApplied",
        "safeMetadata",
    }
)

#: Forbidden payload keys — a defensive second guard drops them even if a caller
#: smuggles one into ``safeMetadata``.
_FORBIDDEN_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "apiKey",
        "Authorization",
        "authorization",
        "bearer",
        "Bearer",
        "token",
        "accessToken",
        "secret",
        "secretValue",
        "callable",
        "callable_repr",
        "shellCommand",
        "shell_command",
        "sqlStatement",
        "sql",
        "productionPath",
        "production_path",
        "localPath",
        "local_path",
        "pythonImportPath",
        "importPath",
        "modulePath",
        "dynamic_import",
        "dynamicModule",
        "externalUrl",
        "external_url",
        "downloadUrl",
        "download_url",
        "installCommand",
        "install_command",
        "postInstallHook",
        "post_install_hook",
        "preExecutionHook",
        "pre_execution_hook",
    }
)


def redact_plugin_descriptor_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a safe, shallow copy of a plugin-descriptor audit payload.

    Keeps **only** the frozen safe fields, coerces non-JSON values safely, and
    bounds strings. Never raises. A second defensive re-redaction runs at the
    store layer (``sanitize_audit_event``) before append.
    """
    if not isinstance(payload, Mapping):
        return {}
    cleaned: dict[str, Any] = {}
    for key in SAFE_PAYLOAD_FIELDS:
        if key in _FORBIDDEN_PAYLOAD_KEYS:
            continue
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
            cleaned[key] = redact_plugin_descriptor_payload(value)
        elif isinstance(value, (list, tuple)):
            cleaned[key] = [
                redact_plugin_descriptor_payload(v) if isinstance(v, Mapping) else v
                for v in value
                if isinstance(v, (bool, int, float, str))
            ]
        else:
            # bytes / callables / arbitrary objects → drop the value entirely.
            continue
    cleaned["redactionApplied"] = True
    return cleaned


def write_plugin_descriptor_audit(
    *,
    event_type: str,
    plugin_id: str | None = None,
    capability_id: str | None = None,
    permission_class: str | None = None,
    trust_level: str | None = None,
    status: str | None = None,
    blocked_reason: str | None = None,
    dev_only: bool | None = None,
    production_allowed: bool | None = None,
    requires_approval: bool | None = None,
    requires_audit: bool | None = None,
    safe_metadata: Mapping[str, Any] | None = None,
    hermes_home: str | None = None,
) -> AuditStoreWriteResult:
    """Append one ``plugin_descriptor_*`` breadcrumb event to the durable store.

    Returns the :class:`AuditStoreWriteResult`. The ``event_id`` (on success)
    is the correlation id the caller may surface as an audit link. Never raises;
    a store failure is reported in the result and never enables a descriptor.
    """
    if event_type not in PLUGIN_DESCRIPTOR_EVENT_TYPES:
        # Unknown event types are normalized to the load breadcrumb so a caller
        # bug can never produce an un-queryable event.
        event_type = "plugin_descriptor_registry_loaded"

    payload = redact_plugin_descriptor_payload(
        {
            "pluginId": plugin_id,
            "capabilityId": capability_id,
            "permissionClass": permission_class,
            "trustLevel": trust_level,
            "status": status,
            "blockedReason": blocked_reason,
            "devOnly": dev_only,
            "productionAllowed": production_allowed,
            "requiresApproval": requires_approval,
            "requiresAudit": requires_audit,
            "safeMetadata": redact_plugin_descriptor_payload(safe_metadata) if safe_metadata else None,
        }
    )

    summary: dict[str, Any] = {
        "schemaOrigin": "plugin_descriptor_audit_v1",
        "eventType": event_type,
        "redactionApplied": True,
    }
    # Surface the safe payload into summary (sanitized again by the store).
    for key, value in payload.items():
        if value is not None:
            summary[key] = value

    meta: dict[str, Any] = {
        "schemaOrigin": "plugin_descriptor_audit_v1",
        "registryPhase": PLUGIN_DESCRIPTOR_PHASE,
    }

    event = build_audit_event(
        event_type=event_type,
        audit_kind=AUDIT_KIND_INTERNAL,
        source=PLUGIN_DESCRIPTOR_AUDIT_SOURCE,
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
        # Audit failure must NEVER enable a descriptor / grant permission.
        return AuditStoreWriteResult(
            written=False,
            event_id=None,
            sequence=None,
            segment=None,
            rotated=False,
            error_code="plugin_descriptor_audit_write_failed",
            error_message="Plugin descriptor audit write failed.",
        )


__all__ = [
    "PLUGIN_DESCRIPTOR_AUDIT_SOURCE",
    "PLUGIN_DESCRIPTOR_PHASE",
    "PLUGIN_DESCRIPTOR_EVENT_TYPES",
    "SAFE_PAYLOAD_FIELDS",
    "redact_plugin_descriptor_payload",
    "write_plugin_descriptor_audit",
]
