/**
 * Type definitions for the Phase 3D static Plugin Descriptor Registry.
 *
 * Safety:
 *   - No API key, Authorization header, Bearer token, raw secret, callable
 *     repr, shell command, SQL statement, production path, local plugin path,
 *     dynamic import path, external URL, download URL, or install command ever
 *     appears in these types.
 *   - The registry describes future plugin descriptors only; it never grants
 *     permission, never loads a plugin, never executes a plugin.
 *   - The UI is read-only: there are no enable/disable/install/execute controls.
 *   - No plugin runtime, no plugin loader, no dynamic loading, no local plugin
 *     directory loading, no remote registry / marketplace / external plugin
 *     fetch.
 */

/** Plugin trust level (frozen). */
export type PluginTrustLevel =
  | 'trusted_builtin_code'
  | 'trusted_static_descriptor'
  | 'dev_reviewed_descriptor'
  | 'experimental_disabled_descriptor'
  | 'external_forbidden'
  | 'unknown_forbidden'
  | 'production_forbidden'

/** Plugin lifecycle status (frozen). None is an executable lifecycle. */
export type PluginStatus =
  | 'planned'
  | 'declared'
  | 'validated'
  | 'visible'
  | 'disabled'
  | 'blocked'
  | 'deprecated'
  | 'removed'

/** Plugin execution mode (frozen). None represents runtime execution. */
export type PluginExecutionMode = 'none' | 'descriptor_only' | 'read_only_descriptor' | 'disabled_runtime'

/** Plugin descriptor source (frozen). */
export type PluginSource =
  | 'builtin_static'
  | 'tracked_static_descriptor'
  | 'dev_reviewed_descriptor'
  | 'experimental_disabled'
  | 'external_forbidden'
  | 'unknown_forbidden'
  | 'production_forbidden'

/** Permission class — shared with the Phase 3C Capability Registry. */
export type PluginPermissionClass =
  | 'READ_ONLY'
  | 'WRITE_PREVIEW'
  | 'WRITE_CONFIRM'
  | 'ROLLBACK_CONFIRM'
  | 'LIVE_PROVIDER_GATED'
  | 'ADMIN_FORBIDDEN'
  | 'EXTERNAL_FORBIDDEN'
  | 'PRODUCTION_FORBIDDEN'

/** Read-only safe record for a single plugin descriptor (value-free). */
export interface PluginDescriptorDetail {
  readonly pluginId: string
  readonly displayName: string
  readonly description: string
  readonly version?: string
  readonly owner?: string
  readonly source: PluginSource
  readonly trustLevel: PluginTrustLevel
  readonly status: PluginStatus
  readonly capabilityBindings: readonly string[]
  readonly permissionClass: PluginPermissionClass
  readonly executionMode: PluginExecutionMode
  readonly requiresApproval: boolean
  readonly requiresDryRun: boolean
  readonly requiresConfirmation: boolean
  readonly requiresAudit: boolean
  readonly requiresBudget: boolean
  readonly requiresKillSwitch: boolean
  readonly devOnly: boolean
  readonly productionAllowed: boolean
  readonly disabledByDefault: boolean
  readonly blockedReason: string | null
  readonly metadataSchema?: string
  readonly redactionApplied: boolean
}

/** The frozen descriptor-registry summary block surfaced under GET /status data. */
export interface PluginDescriptorRegistrySummary {
  readonly status: 'enabled' | 'validation_failed'
  readonly registryVersion: string
  readonly descriptorCount: number
  readonly visibleCount: number
  readonly disabledCount: number
  readonly blockedCount: number
  readonly devOnly: boolean
  readonly productionAllowed: boolean
  readonly pluginRuntimeImplemented: boolean
  readonly pluginLoaderImplemented: boolean
  readonly dynamicLoadingAllowed: boolean
  readonly localPluginDirectoryLoadingAllowed: boolean
  readonly remoteRegistryAllowed: boolean
  readonly marketplaceAllowed: boolean
  readonly externalPluginFetchAllowed: boolean
  readonly providerGeneratedPluginAllowed: boolean
  readonly llmGeneratedPluginInstallAllowed: boolean
  readonly pluginExecutionAllowed: boolean
  readonly newRouteIntroduced: boolean
  readonly routeGovernanceExpected: string
  readonly validation: { readonly valid: boolean; readonly errorCount: number; readonly warningCount: number }
  readonly redactionApplied: boolean
}
