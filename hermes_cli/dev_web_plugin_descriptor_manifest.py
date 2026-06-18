"""Phase 3D Plugin Descriptor Registry — Static Manifest (single source of truth).

This module is the **static manifest**: a tracked, reviewable, deterministic
data structure that declares every plugin *descriptor* the dev instance knows
about. It is descriptor-only: it describes future plugin descriptors; it never
loads a plugin, never executes a plugin, never imports code, never fetches a
remote manifest, never reads a local plugin directory, and never carries a
secret.

Hard guarantees (frozen, see docs/webui/phase-3d-*.md):

  - **Static.** A literal Python tuple of dicts. No runtime plugin path, no
    ``importlib``, no ``__import__``, no path-based file load, no directory
    scan, no remote fetch, no marketplace.
  - **Deterministic.** Same source → same registry output. No wall-clock
    sampling: ``CREATED_AT`` / ``UPDATED_AT`` are pinned constants.
  - **No execution surface.** No entry carries a forbidden field
    (``pythonImportPath``, ``callable``, ``shellCommand``, ``externalUrl``,
    ``downloadUrl``, ``pluginPackage``, ``dynamicModule``, ``evalCode``,
    ``execCode``, ``sqlStatement``, ``productionPath``, ``apiKey``,
    ``Authorization``, ``secret``, ``localPath``, ``remoteUrl``,
    ``installCommand``, ``postInstallHook``, ``preExecutionHook``,
    ``arbitraryArgs``, …). The registry describes descriptors; it never
    invokes them.
  - **Capability-bound.** Every descriptor binds **only** to existing Phase 3C
    Capability Registry capabilityIds. No descriptor introduces a new
    capabilityId or a new permission class. The descriptor inherits the
    most-restrictive permission class among its bindings.
  - **Dev-only + disabled-by-default.** Every entry has ``devOnly = True``,
    ``productionAllowed = False`` and ``disabledByDefault = True``. No
    descriptor may be executable. There is no plugin runtime and no plugin
    loader in this version.

The manifest is loaded by :mod:`hermes_cli.dev_web_plugin_descriptor_registry`,
which validates it (schema + capability-binding + permission-inheritance +
trust policy) before exposing anything. Loading the manifest never performs a
side effect.

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
Status: implemented. No plugin runtime execution, no plugin loader execution,
        no dynamic loading, no local plugin directory loading, no remote
        registry, no marketplace, no external plugin fetch.
"""

from __future__ import annotations

from typing import Any

#: Frozen manifest version. Bumped only under an authorized scope freeze.
MANIFEST_VERSION: str = "phase3d-static-descriptor-v1"

#: Pinned creation / update timestamps (NOT wall-clock derived). The manifest
#: is deterministic; the registry loader never samples the clock.
CREATED_AT: str = "2026-06-18T00:00:00Z"
UPDATED_AT: str = "2026-06-18T00:00:00Z"

#: The static manifest. Each entry is a plain dict. Field set is validated
#: against :mod:`hermes_cli.dev_web_plugin_descriptor_schema`. Capability
#: bindings are validated against the Phase 3C Capability Registry. Ordering is
#: deterministic (visible registry views → disabled bridges → blocked
#: forbidden categories) and stable across loads.
STATIC_PLUGIN_DESCRIPTOR_MANIFEST: tuple[dict[str, Any], ...] = (
    # ── Visible descriptor-only views (bind Phase 3C registry read capabilities) ──
    {
        "pluginId": "plugin.descriptor.registry_status",
        "displayName": "Plugin Descriptor Registry Status",
        "description": (
            "Read-only plugin descriptor registry summary surfaced under the existing "
            "/status block. Descriptor only — does not execute a plugin."
        ),
        "version": MANIFEST_VERSION,
        "owner": "phase-3d",
        "source": "builtin_static",
        "trustLevel": "trusted_static_descriptor",
        "status": "visible",
        "capabilityBindings": ("registry.capability_registry_status",),
        "permissionClass": "READ_ONLY",
        "executionMode": "descriptor_only",
        "requiresApproval": False,
        "requiresDryRun": False,
        "requiresConfirmation": False,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
        "metadataSchema": "plugin_descriptor_status_v1",
        "createdAt": CREATED_AT,
        "updatedAt": UPDATED_AT,
    },
    {
        "pluginId": "plugin.descriptor.capability_binding_view",
        "displayName": "Plugin Descriptor Capability Binding View",
        "description": (
            "Read-only view of how plugin descriptors bind to Phase 3C capabilityIds. "
            "Descriptor only — does not execute a plugin or grant permission."
        ),
        "version": MANIFEST_VERSION,
        "owner": "phase-3d",
        "source": "tracked_static_descriptor",
        "trustLevel": "trusted_static_descriptor",
        "status": "visible",
        "capabilityBindings": ("registry.capability_registry_detail",),
        "permissionClass": "READ_ONLY",
        "executionMode": "descriptor_only",
        "requiresApproval": False,
        "requiresDryRun": False,
        "requiresConfirmation": False,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
        "metadataSchema": "plugin_descriptor_binding_v1",
        "createdAt": CREATED_AT,
        "updatedAt": UPDATED_AT,
    },
    {
        "pluginId": "plugin.descriptor.audit_view",
        "displayName": "Plugin Descriptor Audit View",
        "description": (
            "Read-only view of redacted plugin_descriptor_* audit breadcrumbs (safe "
            "fields only). Descriptor only — does not execute a plugin."
        ),
        "version": MANIFEST_VERSION,
        "owner": "phase-3d",
        "source": "tracked_static_descriptor",
        "trustLevel": "trusted_static_descriptor",
        "status": "visible",
        "capabilityBindings": ("registry.capability_registry_audit",),
        "permissionClass": "READ_ONLY",
        "executionMode": "descriptor_only",
        "requiresApproval": False,
        "requiresDryRun": False,
        "requiresConfirmation": False,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
        "metadataSchema": "plugin_descriptor_audit_v1",
        "createdAt": CREATED_AT,
        "updatedAt": UPDATED_AT,
    },
    # ── Disabled descriptor-only bridges (inherit bound capability permission) ───
    {
        "pluginId": "plugin.descriptor.read_only_tool_bridge",
        "displayName": "Plugin Descriptor Read-only Tool Bridge",
        "description": (
            "Descriptor-only bridge to read-only tool capabilities. Disabled by "
            "default — does not execute a tool, does not grant permission."
        ),
        "version": MANIFEST_VERSION,
        "owner": "phase-3d",
        "source": "tracked_static_descriptor",
        "trustLevel": "dev_reviewed_descriptor",
        "status": "disabled",
        "capabilityBindings": (
            "tool.read.tool_policy_read",
            "tool.read.route_governance_read",
        ),
        "permissionClass": "READ_ONLY",
        "executionMode": "descriptor_only",
        "requiresApproval": False,
        "requiresDryRun": False,
        "requiresConfirmation": False,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
        "metadataSchema": "plugin_descriptor_tool_bridge_v1",
        "createdAt": CREATED_AT,
        "updatedAt": UPDATED_AT,
    },
    {
        "pluginId": "plugin.descriptor.sandbox_write_preview_bridge",
        "displayName": "Plugin Descriptor Sandbox Write-preview Bridge",
        "description": (
            "Descriptor-only bridge to dev-sandbox write capabilities. Inherits "
            "WRITE_CONFIRM; disabled by default; never performs a real write."
        ),
        "version": MANIFEST_VERSION,
        "owner": "phase-3d",
        "source": "tracked_static_descriptor",
        "trustLevel": "dev_reviewed_descriptor",
        "status": "disabled",
        "capabilityBindings": (
            "tool.sandbox.dev_sandbox_file_write",
            "tool.sandbox.dev_sandbox_file_append",
            "tool.sandbox.dev_sandbox_file_patch",
        ),
        "permissionClass": "WRITE_CONFIRM",
        "executionMode": "descriptor_only",
        "requiresApproval": True,
        "requiresDryRun": True,
        "requiresConfirmation": True,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
        "metadataSchema": "plugin_descriptor_sandbox_bridge_v1",
        "createdAt": CREATED_AT,
        "updatedAt": UPDATED_AT,
    },
    {
        "pluginId": "plugin.descriptor.provider_boundary_bridge",
        "displayName": "Plugin Descriptor Provider Boundary Bridge",
        "description": (
            "Descriptor-only bridge to the real-provider boundary (read-only). "
            "Disabled by default — does not call a provider, does not grant permission."
        ),
        "version": MANIFEST_VERSION,
        "owner": "phase-3d",
        "source": "tracked_static_descriptor",
        "trustLevel": "dev_reviewed_descriptor",
        "status": "disabled",
        "capabilityBindings": (
            "provider.real_boundary_status",
            "provider.real_request_preview",
        ),
        "permissionClass": "READ_ONLY",
        "executionMode": "descriptor_only",
        "requiresApproval": False,
        "requiresDryRun": False,
        "requiresConfirmation": False,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
        "metadataSchema": "plugin_descriptor_provider_bridge_v1",
        "createdAt": CREATED_AT,
        "updatedAt": UPDATED_AT,
    },
    {
        "pluginId": "plugin.descriptor.workflow_step_bridge",
        "displayName": "Plugin Descriptor Workflow Step Bridge",
        "description": (
            "Descriptor-only bridge to read-only workflow steps. Disabled by "
            "default — does not advance a workflow, does not grant permission."
        ),
        "version": MANIFEST_VERSION,
        "owner": "phase-3d",
        "source": "tracked_static_descriptor",
        "trustLevel": "dev_reviewed_descriptor",
        "status": "disabled",
        "capabilityBindings": (
            "workflow.step.read_only_tool",
            "workflow.step.manual_note",
        ),
        "permissionClass": "READ_ONLY",
        "executionMode": "descriptor_only",
        "requiresApproval": False,
        "requiresDryRun": False,
        "requiresConfirmation": False,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
        "metadataSchema": "plugin_descriptor_workflow_bridge_v1",
        "createdAt": CREATED_AT,
        "updatedAt": UPDATED_AT,
    },
    # ── Blocked descriptors (bind Phase 3C forbidden capabilities) ───────────────
    {
        "pluginId": "plugin.descriptor.dynamic_plugin_load_blocked",
        "displayName": "Blocked — Dynamic Plugin Load",
        "description": (
            "Descriptor declaring dynamic plugin / importlib / path-based loading as "
            "permanently blocked. Described only; never loaded."
        ),
        "version": MANIFEST_VERSION,
        "owner": "phase-3d",
        "source": "external_forbidden",
        "trustLevel": "external_forbidden",
        "status": "blocked",
        "capabilityBindings": ("capability.forbidden.dynamic_plugin_load",),
        "permissionClass": "EXTERNAL_FORBIDDEN",
        "executionMode": "descriptor_only",
        "requiresApproval": True,
        "requiresDryRun": False,
        "requiresConfirmation": True,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
        "blockedReason": "dynamic_plugin_load_is_forbidden",
        "metadataSchema": "plugin_descriptor_forbidden_v1",
        "createdAt": CREATED_AT,
        "updatedAt": UPDATED_AT,
    },
    {
        "pluginId": "plugin.descriptor.remote_registry_blocked",
        "displayName": "Blocked — Remote Registry",
        "description": (
            "Descriptor declaring a remote plugin registry / remote manifest fetch as "
            "permanently blocked. Described only; never fetched."
        ),
        "version": MANIFEST_VERSION,
        "owner": "phase-3d",
        "source": "external_forbidden",
        "trustLevel": "external_forbidden",
        "status": "blocked",
        "capabilityBindings": ("capability.forbidden.remote_registry",),
        "permissionClass": "EXTERNAL_FORBIDDEN",
        "executionMode": "descriptor_only",
        "requiresApproval": True,
        "requiresDryRun": False,
        "requiresConfirmation": True,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
        "blockedReason": "remote_registry_is_forbidden",
        "metadataSchema": "plugin_descriptor_forbidden_v1",
        "createdAt": CREATED_AT,
        "updatedAt": UPDATED_AT,
    },
    {
        "pluginId": "plugin.descriptor.marketplace_blocked",
        "displayName": "Blocked — Marketplace",
        "description": (
            "Descriptor declaring a plugin marketplace as permanently blocked. "
            "Described only; never reachable."
        ),
        "version": MANIFEST_VERSION,
        "owner": "phase-3d",
        "source": "external_forbidden",
        "trustLevel": "external_forbidden",
        "status": "blocked",
        "capabilityBindings": ("capability.forbidden.marketplace",),
        "permissionClass": "EXTERNAL_FORBIDDEN",
        "executionMode": "descriptor_only",
        "requiresApproval": True,
        "requiresDryRun": False,
        "requiresConfirmation": True,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
        "blockedReason": "marketplace_is_forbidden",
        "metadataSchema": "plugin_descriptor_forbidden_v1",
        "createdAt": CREATED_AT,
        "updatedAt": UPDATED_AT,
    },
    {
        "pluginId": "plugin.descriptor.external_execution_blocked",
        "displayName": "Blocked — External Execution",
        "description": (
            "Descriptor declaring external execution (shell / database mutation / "
            "external HTTP) as permanently blocked. Described only; never executed."
        ),
        "version": MANIFEST_VERSION,
        "owner": "phase-3d",
        "source": "external_forbidden",
        "trustLevel": "external_forbidden",
        "status": "blocked",
        "capabilityBindings": (
            "capability.forbidden.external_http",
            "capability.forbidden.shell",
            "capability.forbidden.database_mutation",
        ),
        "permissionClass": "EXTERNAL_FORBIDDEN",
        "executionMode": "descriptor_only",
        "requiresApproval": True,
        "requiresDryRun": False,
        "requiresConfirmation": True,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
        "blockedReason": "external_execution_is_forbidden",
        "metadataSchema": "plugin_descriptor_forbidden_v1",
        "createdAt": CREATED_AT,
        "updatedAt": UPDATED_AT,
    },
    {
        "pluginId": "plugin.descriptor.production_operation_blocked",
        "displayName": "Blocked — Production Operation",
        "description": (
            "Descriptor declaring a production operation (production home / production "
            "database) as permanently blocked. Described only; never reached."
        ),
        "version": MANIFEST_VERSION,
        "owner": "phase-3d",
        "source": "production_forbidden",
        "trustLevel": "production_forbidden",
        "status": "blocked",
        "capabilityBindings": ("capability.forbidden.production_operation",),
        "permissionClass": "PRODUCTION_FORBIDDEN",
        "executionMode": "descriptor_only",
        "requiresApproval": True,
        "requiresDryRun": False,
        "requiresConfirmation": True,
        "requiresAudit": True,
        "requiresBudget": False,
        "requiresKillSwitch": False,
        "devOnly": True,
        "productionAllowed": False,
        "disabledByDefault": True,
        "blockedReason": "production_operation_is_forbidden",
        "metadataSchema": "plugin_descriptor_forbidden_v1",
        "createdAt": CREATED_AT,
        "updatedAt": UPDATED_AT,
    },
)


def get_static_manifest() -> tuple[dict[str, Any], ...]:
    """Return the frozen static manifest (a fresh tuple reference).

    The manifest is immutable; callers must not mutate entries. The registry
    loader copies the safe fields it exposes.
    """
    return STATIC_PLUGIN_DESCRIPTOR_MANIFEST


__all__ = [
    "MANIFEST_VERSION",
    "CREATED_AT",
    "UPDATED_AT",
    "STATIC_PLUGIN_DESCRIPTOR_MANIFEST",
    "get_static_manifest",
]
