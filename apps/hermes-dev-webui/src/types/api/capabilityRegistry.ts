/**
 * Type definitions for the Phase 3C static Capability Registry.
 *
 * Safety:
 *   - No API key, Authorization header, Bearer token, raw secret, callable
 *     repr, shell command, SQL statement, production path, local plugin path,
 *     dynamic import path, or external URL ever appears in these types.
 *   - The registry describes capabilities only; it never grants permission.
 *   - The UI is read-only: there are no enable/disable/promote/delete controls.
 */

/** Capability category (frozen). */
export type CapabilityCategory =
  | 'tool'
  | 'provider'
  | 'workflow'
  | 'sandbox'
  | 'audit'
  | 'registry'
  | 'system'

/** Capability lifecycle status (frozen). */
export type CapabilityStatus = 'enabled' | 'disabled' | 'blocked' | 'planned' | 'deprecated'

/** Permission class (frozen). The three *_FORBIDDEN classes are terminal. */
export type CapabilityPermissionClass =
  | 'READ_ONLY'
  | 'WRITE_PREVIEW'
  | 'WRITE_CONFIRM'
  | 'ROLLBACK_CONFIRM'
  | 'LIVE_PROVIDER_GATED'
  | 'ADMIN_FORBIDDEN'
  | 'EXTERNAL_FORBIDDEN'
  | 'PRODUCTION_FORBIDDEN'

/** Trust level (frozen). */
export type CapabilityTrustLevel =
  | 'BUILTIN_VERIFIED'
  | 'DEV_STATIC_MANIFEST'
  | 'EXPERIMENTAL_DISABLED'
  | 'EXTERNAL_FORBIDDEN'
  | 'UNKNOWN_FORBIDDEN'

/** Execution mode (frozen). */
export type CapabilityExecutionMode = 'none' | 'read_only' | 'dry_run' | 'confirmed_execute' | 'manual_live'

/** Route exposure (frozen). */
export type CapabilityRouteExposure = 'existing_route_only' | 'no_route' | 'forbidden_new_route'

/** Read-only safe record for a single capability (value-free). */
export interface CapabilityDetail {
  readonly capabilityId: string
  readonly displayName: string
  readonly description: string
  readonly category: CapabilityCategory
  readonly status: CapabilityStatus
  readonly permissionClass: CapabilityPermissionClass
  readonly trustLevel: CapabilityTrustLevel
  readonly executionMode: CapabilityExecutionMode
  readonly routeExposure: CapabilityRouteExposure
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
  readonly toolBinding?: string
  readonly providerBinding?: string
  readonly workflowBinding?: string
  readonly auditEventPrefix?: string
  readonly metadataSchema?: string
  readonly redactionApplied: boolean
}

/** The frozen registry summary block surfaced under GET /status data. */
export interface CapabilityRegistrySummary {
  readonly status: 'enabled' | 'validation_failed'
  readonly registryVersion: string
  readonly loaded: boolean
  readonly validationPassed: boolean
  readonly capabilityCount: number
  readonly enabledCount: number
  readonly disabledCount: number
  readonly blockedCount: number
  readonly plannedCount: number
  readonly deprecatedCount: number
  readonly permissionClassCounts: Readonly<Record<string, number>>
  readonly trustLevelCounts: Readonly<Record<string, number>>
  readonly categoryCounts: Readonly<Record<string, number>>
  readonly devOnly: boolean
  readonly productionAllowed: boolean
  readonly dynamicLoadingAllowed: boolean
  readonly remoteRegistryAllowed: boolean
  readonly marketplaceAllowed: boolean
  readonly routeGovernanceExpected: string
  readonly validation: { readonly valid: boolean; readonly errorCount: number; readonly warningCount: number }
  readonly redactionApplied: boolean
}
