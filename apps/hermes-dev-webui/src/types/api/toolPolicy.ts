/**
 * TypeScript types for the Dev API tool policy endpoints.
 *
 * Matches the Phase 1G-02 read-only Tool Policy contract.
 * All catalog items have allowed=false and all execution flags are false.
 */

// ── Enum-like union types ──

/** Tool risk level — matches backend ToolRiskLevel enum. */
export type ToolRiskLevel =
  | 'R0'
  | 'R1'
  | 'R2'
  | 'R3'
  | 'R4'
  | 'R5'

/** Tool capability tag — matches backend ToolCapability enum. */
export type ToolCapability =
  | 'PURE_COMPUTE'
  | 'LOCAL_FILE_READ'
  | 'LOCAL_FILE_WRITE'
  | 'DATABASE_READ'
  | 'DATABASE_WRITE'
  | 'NETWORK_READ'
  | 'NETWORK_WRITE'
  | 'PROCESS_EXECUTION'
  | 'CODE_EXECUTION'
  | 'BROWSER_CONTROL'
  | 'DESKTOP_CONTROL'
  | 'CREDENTIAL_USE'
  | 'REMOTE_STATE_MUTATION'
  | 'MESSAGE_SEND'
  | 'MEDIA_GENERATION'
  | 'ADMINISTRATIVE_ACTION'
  | 'SCHEDULING'
  | 'SUB_AGENT_EXECUTION'

/** Derived policy status for a tool. */
export type ToolPolicyStatus =
  | 'PERMANENTLY_DENIED'
  | 'CANDIDATE'
  | 'UNLISTED'
  | 'STATICALLY_ALLOWED'

/** Sort order for catalog queries. */
export type ToolCatalogSort =
  | 'nameAsc'
  | 'nameDesc'
  | 'riskAsc'
  | 'riskDesc'

// ── Policy Status Response ──

/** Execution capability status (all false). */
export interface ToolPolicyExecution {
  readonly implemented: boolean
  readonly enabled: boolean
  readonly providerSchemaSent: boolean
  readonly dispatchAvailable: boolean
  readonly auditAvailable: boolean
}

/** Safety flags (all read-only, no side effects). */
export interface ToolPolicySafety {
  readonly readOnly: boolean
  readonly sideEffects: boolean
  readonly writeEnabled: boolean
  readonly executeAvailable: boolean
  readonly policyMutationAvailable: boolean
}

/** Global limits from the static policy module. */
export interface ToolPolicyLimits {
  readonly maxArgumentPayloadBytes: number
  readonly maxArgumentNestingDepth: number
  readonly maxArgumentStringLength: number
  readonly maxArgumentArrayLength: number
  readonly defaultR0TimeoutSeconds: number
  readonly defaultR1TimeoutSeconds: number
  readonly maxToolTimeoutSeconds: number
  readonly maxToolCallsPerRun: number
  readonly maxGlobalConcurrency: number
  readonly maxConcurrencyPerRun: number
  readonly maxSerializedOutputBytes: number
  readonly maxAgentVisibleOutputBytes: number
  readonly maxWebPreviewOutputBytes: number
}

/** Risk counts keyed by risk level string. */
export type ToolRiskCounts = Readonly<Record<ToolRiskLevel, number>>

/** Complete policy status response — GET /tools/policy data. */
export interface ToolPolicyStatusResponse {
  readonly mode: string
  readonly inventoryCount: number
  readonly riskCounts: ToolRiskCounts
  readonly permanentDenylistCount: number
  readonly candidateAllowlistCount: number
  readonly enabledAllowlistCount: number
  readonly execution: ToolPolicyExecution
  readonly limits: ToolPolicyLimits
  readonly safety: ToolPolicySafety
}

// ── Catalog Item ──

/** Single tool entry in the catalog response. */
export interface ToolCatalogItem {
  readonly canonicalName: string
  readonly primaryRisk: ToolRiskLevel
  readonly riskRank: string
  readonly capabilities: readonly ToolCapability[]
  readonly permanentlyDenied: boolean
  readonly candidateAllowlisted: boolean
  readonly staticallyAllowed: boolean
  readonly allowed: boolean
  readonly policyStatus: ToolPolicyStatus
  readonly reasonCode: string
  readonly sourceModule: string
  readonly rationalePreview: string
  readonly executionAvailable: boolean
  readonly schemaPreviewAvailable: boolean
  readonly dryRunAvailable: boolean
}

// ── Catalog Response ──

/** Active filters applied in the catalog query. */
export interface ToolCatalogFiltersResponse {
  readonly q: string | null
  readonly risk: string | null
  readonly capability: string | null
  readonly policyStatus: string | null
  readonly sort: string
}

/** Summary counts in catalog response. */
export interface ToolCatalogSummary {
  readonly inventoryCount: number
  readonly permanentDenylistCount: number
  readonly candidateAllowlistCount: number
  readonly enabledAllowlistCount: number
}

/** Safety flags in catalog response. */
export interface ToolCatalogSafety {
  readonly readOnly: boolean
  readonly sideEffects: boolean
  readonly executeAvailable: boolean
}

/** Complete catalog response — GET /tools/catalog data. */
export interface ToolCatalogResponse {
  readonly items: readonly ToolCatalogItem[]
  readonly page: number
  readonly pageSize: number
  readonly total: number
  readonly totalPages: number
  readonly filters: ToolCatalogFiltersResponse
  readonly summary: ToolCatalogSummary
  readonly safety: ToolCatalogSafety
}

// ── Query Parameters ──

/** Parameters for GET /tools/catalog (client-side filter state). */
export interface ToolCatalogFilters {
  readonly q: string
  readonly risk: ToolRiskLevel | undefined
  readonly capability: ToolCapability | undefined
  readonly policyStatus: ToolPolicyStatus | undefined
  readonly page: number
  readonly pageSize: number
  readonly sort: ToolCatalogSort
}
