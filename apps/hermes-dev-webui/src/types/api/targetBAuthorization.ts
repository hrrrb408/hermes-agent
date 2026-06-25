/**
 * Target B Authorization Package view-model types (Phase 4C).
 *
 * Pure, value-free TypeScript shapes for the Dev WebUI read-only **Target B
 * Authorization & Gate Resolution Package** region. Phase 4C builds the
 * **authorization-material validation structure** on top of the Phase 4B gated
 * engineering layers: the human approval record schema, the trust token
 * validation pipeline, the trusted publisher set, the production signature
 * verifier authorization adapter, the sandbox worker lifecycle approval, the
 * registry trust policy approval, the network allowlist, the secret handling
 * policy, the rollback / incident plan approval, the route authorization plan,
 * the P0 pending-gate resolution evaluator, and the unified enablement
 * readiness evaluator — while keeping **every gate fail-closed**.
 *
 * These types mirror the deterministic, redacted, conservative projections of
 * the backend Phase 4C authorization layers
 * (`hermes_cli/dev_web_target_b_*authorization*` / `*_policy*` /
 * `*_lifecycle*` / `*_rollback*` / `*_p0_gate_resolution*` /
 * `*_enablement_readiness*`) and carry ONLY safe, value-free fields: no API
 * key, Authorization, Bearer, secret, callable repr, shell command, SQL
 * statement, production path, local plugin path, dynamic import path,
 * executable entrypoint, real external URL, download URL, install command, real
 * registry token, real trust token, real plugin signature, or production home
 * path.
 *
 * Nothing here fabricates an approval, bypasses P0, mints a trust token, treats
 * metadata / a static manifest / an AI-generated approval as authorization,
 * flips the production runtime to GO, provisions a trust token, authorizes a
 * signature verifier, enables a sandbox worker, opens a registry, opens a
 * marketplace, reads a real API key, authorizes a route, or performs a side
 * effect. The readiness status is frozen BLOCKED; every authorization verdict
 * is frozen NO-GO; the trust token is frozen not provisioned; P0 resolved stays
 * 0; and the route baseline is frozen unchanged (34/34/5/0/1/1).
 */

/** Schema version mirrored from the backend Phase 4C authorization report. */
export const TARGET_B_AUTHORIZATION_SCHEMA_VERSION = 'phase-4c-target-b-authorization-v1' as const

/** Frozen phase label for the Target B authorization region. */
export const TARGET_B_AUTHORIZATION_PHASE = 'Phase 4C' as const

/** Frozen route-governance baseline (unchanged by this read-only surface). */
export const TARGET_B_AUTHORIZATION_ROUTE_BASELINE = '34/34/5/0/1/1' as const

/** A frozen NO-GO authorization verdict (never GO / never authorized). */
export type TargetBAuthorizationNoGoVerdict = 'NO-GO'

/** A frozen authorization-package status — implemented, never an enablement. */
export type TargetBAuthorizationFlag = 'AUTHORIZATION_PACKAGE_IMPLEMENTED'

/** The four frozen enablement readiness statuses. */
export type TargetBReadinessStatus =
  | 'BLOCKED'
  | 'AUTHORIZATION_PACKAGE_INCOMPLETE'
  | 'AUTHORIZATION_READY_BUT_NOT_ENABLED'
  | 'ENABLEMENT_ALLOWED_BY_POLICY'

/** A single Phase 4C authorization sub-layer on the status board. */
export interface TargetBAuthorizationLayer {
  readonly key: string
  readonly layer: string
  readonly status: 'NOT_AUTHORIZED' | 'DESIGN_READY_ONLY'
  readonly authorized: false
  readonly fixtureOnly: boolean
  readonly riskLevel: string
  readonly requiredMaterial: string
}

/** The conservative Target B authorization package summary. */
export interface TargetBAuthorizationSummary {
  readonly targetName: 'Target B — Production Runtime / Real Plugin Ecosystem'
  readonly authorizationStatus: TargetBAuthorizationFlag
  readonly readinessStatus: 'BLOCKED'
  readonly productionEnablementAllowed: false
  readonly productionRuntime: TargetBAuthorizationNoGoVerdict
  readonly registry: TargetBAuthorizationNoGoVerdict
  readonly marketplace: TargetBAuthorizationNoGoVerdict
  readonly webuiExecution: TargetBAuthorizationNoGoVerdict
  readonly approvalAuthorization: TargetBAuthorizationNoGoVerdict
  readonly productionRollout: TargetBAuthorizationNoGoVerdict
  readonly trustTokenProvisioned: false
  readonly productionSignatureVerifierAuthorized: false
  readonly p0Total: 24
  readonly p0Resolved: 0
  readonly p0PartialEvidence: 19
  readonly p0PendingHumanReview: 5
  readonly pendingHumanReviewGates: readonly string[]
  readonly requiredBeforeEnable: readonly string[]
}

/** The frozen human approval gate projection. */
export interface TargetBHumanApprovalProjection {
  readonly approvalPresent: false
  readonly valid: false
  readonly productionValid: false
  readonly fakeApprovalRejected: true
  readonly aiApprovalRejected: true
  readonly metadataApprovalRejected: true
  readonly staticManifestRejected: true
  readonly fixtureOnlyNeverProduction: true
  readonly requiredGateCoverage: readonly string[]
  readonly productionAuthorization: TargetBAuthorizationNoGoVerdict
}

/** The frozen trust token validation projection. */
export interface TargetBTrustTokenProjection {
  readonly provisioned: false
  readonly valid: false
  readonly productionAuthorized: false
  readonly fakeTokenRejected: true
  readonly aiTokenRejected: true
  readonly metadataTokenRejected: true
  readonly noSecretRead: true
  readonly noProductionHomeAccess: true
  readonly productionAuthorization: TargetBAuthorizationNoGoVerdict
}

/** The frozen trusted publisher set projection. */
export interface TargetBTrustedPublisherProjection {
  readonly trustedPublishersCount: 0
  readonly unknownPublisherRejected: true
  readonly marketplacePublisherRejected: true
  readonly unsignedPublisherRejected: true
  readonly wildcardPublisherRejected: true
  readonly overbroadPermissionsRejected: true
  readonly productionAuthorization: TargetBAuthorizationNoGoVerdict
}

/** The frozen production signature verifier authorization projection. */
export interface TargetBProductionSignatureProjection {
  readonly verifierInterfaceImplemented: true
  readonly productionVerifierAuthorized: false
  readonly fixtureVerifierOnly: true
  readonly realVerificationEnabled: false
  readonly fixtureSignatureDoesNotImplyProduction: true
  readonly forgedSignatureRejected: true
  readonly unknownPublisherRejected: true
  readonly mismatchedChecksumRejected: true
  readonly productionAuthorization: TargetBAuthorizationNoGoVerdict
}

/** The frozen sandbox worker lifecycle approval projection. */
export interface TargetBSandboxLifecycleProjection {
  readonly lifecycleApproved: false
  readonly workerStartAllowed: false
  readonly processSpawnAllowed: false
  readonly networkAllowed: false
  readonly filesystemWriteAllowed: false
  readonly secretsAllowed: false
  readonly killSwitchArmed: false
  readonly productionGatewayUntouched: true
  readonly productionAuthorization: TargetBAuthorizationNoGoVerdict
}

/** The frozen registry / network / secret policy projection. */
export interface TargetBPolicyProjection {
  readonly registryDisabled: true
  readonly registryFetchAllowed: false
  readonly marketplaceAllowed: false
  readonly wildcardDomainsRejected: true
  readonly networkAllowlistPresent: false
  readonly networkDestinationsAllowed: 0
  readonly wildcardHostsDenied: true
  readonly cleartextHttpDenied: true
  readonly noSocketOpened: true
  readonly secretPolicyDefaultDeny: true
  readonly secretValuesRedacted: true
  readonly noSecretRead: true
  readonly productionAuthorization: TargetBAuthorizationNoGoVerdict
}

/** The frozen rollback / incident plan approval projection. */
export interface TargetBRollbackIncidentProjection {
  readonly rollbackPlanPresent: true
  readonly rollbackPlanApproved: false
  readonly incidentPlanApproved: false
  readonly killSwitchReady: 'DESIGN_READY_ONLY'
  readonly productionRollbackAuthorized: false
  readonly productionRollout: TargetBAuthorizationNoGoVerdict
  readonly productionGatewayUntouched: true
  readonly productionAuthorization: TargetBAuthorizationNoGoVerdict
}

/** The frozen route authorization plan projection. */
export interface TargetBRouteAuthorizationProjection {
  readonly routeAuthorized: false
  readonly proposedRoutesCount: number
  readonly proposedRoutesRegistered: 0
  readonly openapiDelta: 0
  readonly runtimeRouteDelta: 0
  readonly routeGovernanceBaseline: typeof TARGET_B_AUTHORIZATION_ROUTE_BASELINE
  readonly backendRoutesChanged: false
  readonly productionAuthorization: TargetBAuthorizationNoGoVerdict
}

/** A single pending P0 gate and its resolution state. */
export interface TargetBP0GateCoverageRow {
  readonly gateId: string
  readonly resolved: false
  readonly hasEvidence: boolean
  readonly hasHumanApproval: false
  readonly hasTrustToken: false
}

/** The frozen P0 gate coverage projection. */
export interface TargetBP0GateCoverageProjection {
  readonly p0Total: 24
  readonly p0Resolved: 0
  readonly p0PartialEvidence: 19
  readonly pendingHumanReview: 5
  readonly pendingHumanReviewGates: readonly string[]
  readonly resolvedCountDelta: 0
  readonly coverage: readonly TargetBP0GateCoverageRow[]
  readonly productionAuthorization: TargetBAuthorizationNoGoVerdict
}

/** The frozen enablement readiness projection. */
export interface TargetBEnablementReadinessProjection {
  readonly readinessStatus: 'BLOCKED'
  readonly productionEnablementAllowed: false
  readonly allGatesPass: false
  readonly fixtureOnly: false
  readonly blockers: readonly string[]
  readonly productionAuthorization: TargetBAuthorizationNoGoVerdict
}

/** A single enablement blocker (what must exist before Target B can start). */
export interface TargetBAuthorizationBlocker {
  readonly key: string
  readonly label: string
  readonly resolved: false
  readonly detail: string
}

/** A read-only status chip projected into the region header (non-color text). */
export interface TargetBAuthorizationStatusBadge {
  readonly label: string
}

/** A frozen boundary-banner row (icon kind + explicit non-color text). */
export interface TargetBAuthorizationBoundaryItem {
  readonly kind: 'lock' | 'ban'
  readonly label: string
}

/** A summary card projected for the authorization overview. */
export interface TargetBAuthorizationSummaryCard {
  readonly label: string
  readonly value: string | number
  readonly sub?: string
  readonly tone: 'ok' | 'warn' | 'danger' | 'info'
}

/** Client-side layer filter keys (operate on static data only). */
export type TargetBAuthorizationLayerFilterKey = 'all' | 'NOT_AUTHORIZED' | 'DESIGN_READY_ONLY'

/** The full read-only Target B Authorization view model. */
export interface TargetBAuthorizationViewModel {
  readonly schemaVersion: typeof TARGET_B_AUTHORIZATION_SCHEMA_VERSION
  readonly phase: typeof TARGET_B_AUTHORIZATION_PHASE
  readonly summary: TargetBAuthorizationSummary
  readonly summaryCards: readonly TargetBAuthorizationSummaryCard[]
  readonly authorizationLayers: readonly TargetBAuthorizationLayer[]
  readonly humanApproval: TargetBHumanApprovalProjection
  readonly trustToken: TargetBTrustTokenProjection
  readonly trustedPublishers: TargetBTrustedPublisherProjection
  readonly productionSignature: TargetBProductionSignatureProjection
  readonly sandboxLifecycle: TargetBSandboxLifecycleProjection
  readonly policies: TargetBPolicyProjection
  readonly rollbackIncident: TargetBRollbackIncidentProjection
  readonly routeAuthorization: TargetBRouteAuthorizationProjection
  readonly p0GateCoverage: TargetBP0GateCoverageProjection
  readonly enablementReadiness: TargetBEnablementReadinessProjection
  readonly enablementBlockers: readonly TargetBAuthorizationBlocker[]
  readonly statusBadges: readonly TargetBAuthorizationStatusBadge[]
  readonly boundaryItems: readonly TargetBAuthorizationBoundaryItem[]
  readonly forbiddenActions: readonly string[]
  readonly allowedUiActions: readonly string[]
  readonly routeGovernanceBaseline: typeof TARGET_B_AUTHORIZATION_ROUTE_BASELINE
  readonly backendRoutesChanged: false
}
