/**
 * Governance Hub read-only view-model types (Phase 3L).
 *
 * Pure, value-free TypeScript shapes for the Dev WebUI Unified Read-only Control
 * Center — a read-only summary that aggregates the governance state already
 * surfaced by the Runtime Governance (Phase 3J) and Human Review Governance
 * (Phase 3K) sections. These types mirror the deterministic, redacted,
 * conservative projections of the backend governance modules; they carry ONLY
 * safe fields: no API key, Authorization, Bearer, secret, callable repr, shell
 * command, SQL statement, production path, local plugin path, dynamic import
 * path, external URL, download URL, install command, trust token, or real PID.
 *
 * Nothing here grants permission, loads a plugin, executes a plugin, approves a
 * gate, authorizes a runtime, resolves a P0 gate, provisions a trust token,
 * rolls out production, or performs a side effect. Every P0 count is frozen
 * (resolved 0, partial 19, pending 5); every authorization verdict is frozen
 * NO-GO / not-authorized; every side-effect flag is frozen False; every route
 * count is frozen unchanged (34/34/5/0/1/1, all new-route flags 0).
 */

/** Schema version for the Governance Hub envelope. */
export const GOVERNANCE_HUB_SCHEMA_VERSION = 'phase-3l-governance-hub-v1' as const

/** Frozen route-governance baseline (unchanged by this read-only surface). */
export const GOVERNANCE_HUB_ROUTE_BASELINE = '34/34/5/0/1/1' as const

/** Frozen current phase label. */
export const GOVERNANCE_HUB_CURRENT_PHASE = 'Phase 3L' as const

/** A governance-module lifecycle status (never "authorized"). */
export type GovernanceModuleLifecycle =
  | 'COMPLETE'
  | 'IMPLEMENTED'
  | 'READ_ONLY'

/** A frozen authorization verdict value (always NO-GO / not-authorized). */
export type GovernanceNogoVerdict = 'NO-GO' | 'NOT_AUTHORIZED'

/** A frozen section cross-link target (client-side DevConsole section only). */
export type GovernanceHubLinkTarget = 'runtimeGovernance' | 'humanReview'

/**
 * The conservative governance summary that tops the control center. Every
 * authorization verdict is frozen NO-GO; every P0 count is frozen; the route
 * baseline is frozen unchanged; the production gateway is frozen untouched.
 */
export interface GovernanceHubSummary {
  readonly currentPhase: typeof GOVERNANCE_HUB_CURRENT_PHASE
  readonly runtimeGovernanceStatus: 'COMPLETE'
  readonly humanReviewGovernanceStatus: 'IMPLEMENTED'
  readonly descriptorRegistryStatus: 'IMPLEMENTED'
  readonly runtimeCliStatus: 'COMPLETE'
  readonly readOnlyWebuiStatus: 'COMPLETE'
  readonly p0Total: 24
  readonly p0Resolved: 0
  readonly p0Partial: 19
  readonly p0PendingHumanReview: 5
  readonly routeGovernanceUnchanged: true
  readonly productionGatewayUntouched: true
  readonly productionRuntimeAuthorization: 'NO-GO'
  readonly implementationAuthorization: 'NO-GO'
  readonly productionRollout: 'NO-GO'
}

/** A single governance module on the status board. */
export interface GovernanceModuleStatus {
  readonly key: string
  readonly name: string
  readonly phase: string
  readonly status: GovernanceModuleLifecycle
  readonly evidenceSummary: string
  readonly routeImpact: 'No new route'
  readonly productionImpact: 'No production authorization'
  readonly authorizationImpact: 'NO-GO'
  readonly linkTargetSection?: GovernanceHubLinkTarget
  readonly readOnly: true
}

/** The frozen route-governance projection (exact counts, all new-route flags 0). */
export interface GovernanceRouteSummary {
  readonly openapiPaths: 34
  readonly runtimeRoutes: 34
  readonly toolGetRoutes: 5
  readonly toolWriteHttpRoutes: 0
  readonly toolDryRunRoutes: 1
  readonly toolExecutionRoutes: 1
  readonly newHttpRoutes: 0
  readonly newToolWriteRoutes: 0
  readonly newProviderRoutes: 0
  readonly newPluginRoutes: 0
  readonly newRuntimeRoutes: 0
  readonly format: typeof GOVERNANCE_HUB_ROUTE_BASELINE
}

/** The frozen production-safety projection (every flag is False). */
export interface GovernanceProductionSafety {
  readonly productionGatewayTouched: false
  readonly productionGatewayExpectedUnchanged: true
  readonly devGatewayStarted: false
  readonly dashboardStarted: false
  readonly ports5180And5181Bound: false
  readonly productionHomeAccess: false
  readonly productionStateDbAccess: false
  readonly externalNetwork: false
  readonly realSecretRead: false
  readonly note: string
}

/** The frozen NO-GO decision block. Every dimension is frozen NO-GO / not-authorized. */
export interface GovernanceDecisionSummary {
  readonly implementationAuthorization: 'NO-GO'
  readonly phase3iProductionAuthorization: 'NOT_AUTHORIZED'
  readonly productionRuntimeAuthorization: 'NO-GO'
  readonly newBackendRoute: 'NO-GO'
  readonly approvalBackendRoute: 'NO-GO'
  readonly webuiExecutionRoute: 'NO-GO'
  readonly webuiApprovalAction: 'NO-GO'
  readonly productionRollout: 'NO-GO'
}

/** A single evidence source in the Phase 3 capability-chain trail. */
export interface GovernanceEvidenceSource {
  readonly phase: string
  readonly completedDeliverable: string
  readonly evidenceType: string
  readonly whatItProves: string
  readonly whatItDoesNotProve: string
  readonly authorizationImpact: 'Partial evidence only — no production authorization'
}

/** A frozen NO-GO decision row projected for the decision panel display. */
export interface GovernanceDecisionRow {
  readonly key: string
  readonly label: string
  readonly verdict: GovernanceNogoVerdict
  readonly reason: string
}

/** A frozen boundary-banner row (icon kind + explicit non-color text). */
export interface GovernanceBoundaryItem {
  readonly kind: 'lock' | 'ban'
  readonly label: string
}

/** A read-only status chip projected into the page header (non-color text). */
export interface GovernanceStatusBadge {
  readonly label: string
}

/** A summary card projected for the Governance Hub overview. */
export interface GovernanceSummaryCard {
  readonly label: string
  readonly value: string | number
  readonly sub?: string
  readonly tone: 'ok' | 'warn' | 'danger' | 'info'
}

/** A client-side cross-link to an existing Dev Console section. */
export interface GovernanceHubCrossLink {
  readonly target: GovernanceHubLinkTarget
  readonly label: string
  readonly detail: string
}

/** The full read-only Governance Hub view model. */
export interface GovernanceHubViewModel {
  readonly schemaVersion: typeof GOVERNANCE_HUB_SCHEMA_VERSION
  readonly summary: GovernanceHubSummary
  readonly modules: readonly GovernanceModuleStatus[]
  readonly routeSummary: GovernanceRouteSummary
  readonly productionSafety: GovernanceProductionSafety
  readonly decisions: GovernanceDecisionSummary
  readonly decisionRows: readonly GovernanceDecisionRow[]
  readonly evidenceTrail: readonly GovernanceEvidenceSource[]
  readonly deferredItems: readonly string[]
  readonly crossLinks: readonly GovernanceHubCrossLink[]
  readonly forbiddenActions: readonly string[]
  readonly allowedUiActions: readonly string[]
  readonly routeGovernanceBaseline: typeof GOVERNANCE_HUB_ROUTE_BASELINE
  readonly backendRoutesChanged: false
}
