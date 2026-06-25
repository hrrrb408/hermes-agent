/**
 * Target B Implementation gated view-model types (Phase 4B).
 *
 * Pure, value-free TypeScript shapes for the Dev WebUI read-only **Target B
 * End-to-End Implementation** region. Target B is the *long-term* goal of
 * opening a real production plugin runtime. Phase 4B implements the **full
 * engineering path** for that runtime — every schema, verifier, model, broker,
 * gate, orchestrator, audit, and rollback — while keeping **every capability
 * gated and disabled**.
 *
 * These types mirror the deterministic, redacted, conservative projections of
 * the backend gated implementation layers (`hermes_cli/dev_web_target_b_*.py`)
 * and carry ONLY safe, value-free fields: no API key, Authorization, Bearer,
 * secret, callable repr, shell command, SQL statement, production path, local
 * plugin path, dynamic import path, executable entrypoint, real external URL,
 * download URL, install command, real registry token, real plugin signature, or
 * production home path.
 *
 * Nothing here grants permission, loads a plugin, executes a plugin, fetches a
 * registry, opens a marketplace, reads a real API key, provisions a trust
 * token, approves a gate, authorizes a runtime, or performs a side effect.
 * Every Target B authorization verdict is frozen NO-GO; every capability is
 * frozen disabled; every permission is frozen DENIED_BY_DEFAULT; the production
 * authorization is frozen NO-GO; and P0 resolved stays 0.
 */

/** Schema version mirrored from the backend gated implementation report. */
export const TARGET_B_IMPLEMENTATION_SCHEMA_VERSION = 'phase-4b-target-b-implementation-v1' as const

/** Frozen phase label for the Target B implementation region. */
export const TARGET_B_IMPLEMENTATION_PHASE = 'Phase 4B' as const

/** Frozen route-governance baseline (unchanged by this read-only surface). */
export const TARGET_B_IMPLEMENTATION_ROUTE_BASELINE = '34/34/5/0/1/1' as const

/** A frozen implementation status — scaffold ready, never an enablement. */
export type TargetBImplementationFlag = 'SCAFFOLD_READY'

/** A frozen execution status — always DISABLED. */
export type TargetBExecutionFlag = 'DISABLED'

/** A frozen NO-GO authorization verdict (never GO / never authorized). */
export type TargetBNoGoVerdict = 'NO-GO'

/** A frozen implementation layer lifecycle (never "enabled"). */
export type TargetBLayerLifecycle = 'DESIGNED' | 'SCAFFOLDED_DISABLED'

/** A frozen permission disposition — always denied by default. */
export type TargetBPermissionStatus = 'DENIED_BY_DEFAULT'

/**
 * The conservative Target B implementation summary. Every authorization
 * verdict is frozen NO-GO; every capability is frozen disabled; P0 resolved
 * stays 0; the route baseline is frozen unchanged.
 */
export interface TargetBImplementationSummary {
  readonly targetName: 'Target B — Production Runtime / Real Plugin Ecosystem'
  readonly implementationStatus: TargetBImplementationFlag
  readonly executionStatus: TargetBExecutionFlag
  readonly productionRuntime: TargetBNoGoVerdict
  readonly arbitraryPluginLoading: TargetBNoGoVerdict
  readonly remoteRegistry: TargetBNoGoVerdict
  readonly marketplace: TargetBNoGoVerdict
  readonly webuiExecution: TargetBNoGoVerdict
  readonly approvalAuthorization: TargetBNoGoVerdict
  readonly productionRollout: TargetBNoGoVerdict
  readonly p0Total: 24
  readonly p0Resolved: 0
  readonly p0PartialEvidence: 19
  readonly p0PendingHumanReview: 5
  readonly pendingHumanReviewGates: readonly string[]
  readonly requiredBeforeEnable: readonly string[]
}

/** A single Target B implementation layer on the status board. */
export interface TargetBImplementationLayer {
  readonly key: string
  readonly layer: string
  readonly status: TargetBLayerLifecycle
  readonly enabled: false
  readonly executionCapable: false
  readonly networkCapable: false
  readonly productionCapable: false
  readonly riskLevel: string
  readonly requiredGate: string
}

/** A frozen, fake, non-executable signed plugin package schema preview. */
export interface TargetBPackageSchemaPreview {
  readonly packageId: string
  readonly packageName: string
  readonly version: string
  readonly publisher: string
  readonly manifestVersion: string
  readonly hermesMinVersion: string
  readonly descriptor: string
  readonly capabilities: readonly string[]
  readonly permissions: readonly string[]
  readonly entrypoints: readonly string[]
  readonly checksum: string
  readonly signature: string
  readonly signatureAlgorithm: string
  readonly registrySource: string
  readonly sandboxProfile: string
  readonly exampleOnly: true
  readonly notLoaded: true
  readonly notExecutable: true
}

/** A single permission in the implementation permission model — always denied. */
export interface TargetBImplementationPermissionEntry {
  readonly key: string
  readonly label: string
  readonly risk: string
  readonly currentStatus: TargetBPermissionStatus
  readonly grantable: false
}

/** The frozen plugin permission model (every permission denied by default). */
export interface TargetBImplementationPermissionModel {
  readonly entries: readonly TargetBImplementationPermissionEntry[]
  readonly defaultDisposition: TargetBPermissionStatus
  readonly anyGranted: false
  readonly dangerousPermissionsDenied: true
}

/** A single non-executable capability declaration. */
export interface TargetBCapabilityEntry {
  readonly key: string
  readonly label: string
  readonly executable: false
}

/** The frozen capability declaration model (metadata only). */
export interface TargetBCapabilityModel {
  readonly entries: readonly TargetBCapabilityEntry[]
  readonly anyExecutable: false
}

/** The frozen signature verification layer projection. */
export interface TargetBSignatureVerificationProjection {
  readonly verifierInterfaceImplemented: true
  readonly productionVerifierAuthorized: false
  readonly fixtureVerifierOnly: true
  readonly trusted: false
  readonly productionApproved: false
  readonly unsignedRejected: true
  readonly forgedRejected: true
  readonly marketplaceRejected: true
  readonly unknownPublisherRejected: true
  readonly signatureRequired: true
  readonly productionAuthorization: TargetBNoGoVerdict
}

/** The frozen registry trust policy projection. */
export interface TargetBRegistryTrustProjection {
  readonly registryMode: 'DISABLED'
  readonly networkEnabled: false
  readonly fetchEnabled: false
  readonly marketplaceEnabled: false
  readonly allowUnsigned: false
  readonly trustedPublishersCount: 0
  readonly signatureRequired: true
  readonly registryUrlExample: 'https://registry.example.invalid'
  readonly productionAuthorization: TargetBNoGoVerdict
}

/** The frozen sandbox broker projection. */
export interface TargetBSandboxBrokerProjection {
  readonly brokerInterfaceImplemented: true
  readonly brokerEnabled: false
  readonly executionAllowed: false
  readonly processSpawnAllowed: false
  readonly networkAllowed: false
  readonly filesystemWriteAllowed: false
  readonly secretsAllowed: false
  readonly profileDesignOnly: true
  readonly productionAuthorization: TargetBNoGoVerdict
}

/** The frozen approval / authorization gate projection. */
export interface TargetBApprovalGateProjection {
  readonly humanApprovalRequired: true
  readonly trustTokenProvisioned: false
  readonly humanApprovalValid: false
  readonly fakeApprovalAccepted: false
  readonly aiApprovalAccepted: false
  readonly metadataApprovalAccepted: false
  readonly productionAuthorization: TargetBNoGoVerdict
}

/** The frozen execution policy projection. */
export interface TargetBExecutionPolicyProjection {
  readonly allowed: false
  readonly canExecutePlugin: false
  readonly canLoadPluginPackage: false
  readonly canFetchRegistry: false
  readonly canRenderWebuiExecuteControl: false
  readonly webuiExecuteEnabled: false
  readonly runtimeRouteEnabled: false
  readonly productionRuntimeEnabled: false
  readonly productionAuthorization: TargetBNoGoVerdict
  readonly p0ResolvedCount: 0
  readonly routeGovernanceBaseline: typeof TARGET_B_IMPLEMENTATION_ROUTE_BASELINE
  readonly reasons: readonly string[]
}

/** The frozen audit / rollback projection. */
export interface TargetBAuditRollbackProjection {
  readonly auditPersistence: 'in_memory_only'
  readonly auditPersisted: false
  readonly auditJsonlWritten: false
  readonly secretsRedacted: true
  readonly killSwitchReady: 'DESIGN_READY_ONLY'
  readonly productionRollbackAuthorized: false
  readonly productionRollout: TargetBNoGoVerdict
  readonly productionGatewayUntouched: true
}

/** A single enablement blocker (what must be done before Target B can start). */
export interface TargetBImplementationBlocker {
  readonly key: string
  readonly label: string
  readonly resolved: false
  readonly detail: string
}

/** A read-only status chip projected into the region header (non-color text). */
export interface TargetBImplementationStatusBadge {
  readonly label: string
}

/** A frozen boundary-banner row (icon kind + explicit non-color text). */
export interface TargetBImplementationBoundaryItem {
  readonly kind: 'lock' | 'ban'
  readonly label: string
}

/** A summary card projected for the implementation overview. */
export interface TargetBImplementationSummaryCard {
  readonly label: string
  readonly value: string | number
  readonly sub?: string
  readonly tone: 'ok' | 'warn' | 'danger' | 'info'
}

/** Client-side layer filter keys (operate on static data only). */
export type TargetBLayerFilterKey = 'all' | TargetBLayerLifecycle

/** The full read-only Target B Implementation view model. */
export interface TargetBImplementationViewModel {
  readonly schemaVersion: typeof TARGET_B_IMPLEMENTATION_SCHEMA_VERSION
  readonly phase: typeof TARGET_B_IMPLEMENTATION_PHASE
  readonly summary: TargetBImplementationSummary
  readonly summaryCards: readonly TargetBImplementationSummaryCard[]
  readonly implementationLayers: readonly TargetBImplementationLayer[]
  readonly packageSchema: TargetBPackageSchemaPreview
  readonly permissionModel: TargetBImplementationPermissionModel
  readonly capabilityModel: TargetBCapabilityModel
  readonly signatureVerification: TargetBSignatureVerificationProjection
  readonly registryTrust: TargetBRegistryTrustProjection
  readonly sandboxBroker: TargetBSandboxBrokerProjection
  readonly approvalGate: TargetBApprovalGateProjection
  readonly executionPolicy: TargetBExecutionPolicyProjection
  readonly auditRollback: TargetBAuditRollbackProjection
  readonly enablementBlockers: readonly TargetBImplementationBlocker[]
  readonly statusBadges: readonly TargetBImplementationStatusBadge[]
  readonly boundaryItems: readonly TargetBImplementationBoundaryItem[]
  readonly forbiddenActions: readonly string[]
  readonly allowedUiActions: readonly string[]
  readonly routeGovernanceBaseline: typeof TARGET_B_IMPLEMENTATION_ROUTE_BASELINE
  readonly backendRoutesChanged: false
}
