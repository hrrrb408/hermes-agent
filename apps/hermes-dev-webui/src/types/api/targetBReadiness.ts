/**
 * Target B Readiness read-only view-model types (Phase 4A).
 *
 * Pure, value-free TypeScript shapes for the Dev WebUI read-only **Target B
 * Readiness Scaffold** region. Target B is the *long-term* goal of opening a
 * real production plugin runtime: signed / arbitrary plugin loading, a remote
 * registry, a marketplace, WebUI execution, and a production rollout.
 *
 * Phase 4A implements ONLY the **readiness scaffold** — the architecture models,
 * the disabled interfaces, the permission / approval gate models, the read-only
 * WebUI preview, and the tests proving every dangerous capability is still
 * disabled. It does NOT enable any of those capabilities.
 *
 * These types mirror the deterministic, redacted, conservative projections of
 * the backend disabled scaffold (hermes_cli/dev_web_target_b_readiness.py) and
 * carry ONLY safe, value-free fields: no API key, Authorization, Bearer,
 * secret, callable repr, shell command, SQL statement, production path, local
 * plugin path, dynamic import path, executable entrypoint, real external URL,
 * download URL, install command, real registry token, real plugin signature, or
 * production home path.
 *
 * Nothing here grants permission, loads a plugin, executes a plugin, fetches a
 * registry, opens a marketplace, reads a real API key, provisions a trust token,
 * approves a gate, authorizes a runtime, or performs a side effect. Every Target
 * B authorization verdict is frozen NO-GO; every capability is frozen disabled;
 * every permission is frozen DENIED_BY_DEFAULT; the production authorization is
 * frozen NO-GO; and P0 resolved stays 0.
 */

/** Schema version mirrored from the backend disabled scaffold. */
export const TARGET_B_READINESS_SCHEMA_VERSION = 'phase-4a-target-b-readiness-v1' as const

/** Frozen phase label for the Target B readiness region. */
export const TARGET_B_READINESS_PHASE = 'Phase 4A' as const

/** Frozen route-governance baseline (unchanged by this read-only surface). */
export const TARGET_B_ROUTE_BASELINE = '34/34/5/0/1/1' as const

/**
 * The frozen Target B readiness status. SCAFFOLD_READY means the architecture
 * models and disabled interfaces are drafted — it is NEVER an enablement.
 */
export type TargetBReadinessFlag = 'SCAFFOLD_READY'

/**
 * The frozen Target B execution status — always DISABLED. No production
 * runtime, no arbitrary plugin loading, no registry fetch, no marketplace, no
 * WebUI execution.
 */
export type TargetBExecutionFlag = 'DISABLED'

/** A frozen NO-GO authorization verdict (never GO / never authorized). */
export type TargetBNoGoVerdict = 'NO-GO'

/** A frozen readiness lifecycle for a designed module (never "enabled"). */
export type TargetBModuleLifecycle = 'DESIGNED' | 'SCAFFOLDED_DISABLED'

/** A frozen permission disposition — always denied by default. */
export type TargetBPermissionStatus = 'DENIED_BY_DEFAULT'

/** A frozen checklist status: design readiness vs enablement-blocked. */
export type TargetBChecklistStatus = 'ready' | 'blocked'

/** A risk level projected for an architecture module (read-only text). */
export type TargetBRiskLevel = 'high' | 'medium' | 'critical'

/**
 * The conservative Target B readiness summary. Every authorization verdict is
 * frozen NO-GO; every capability is frozen disabled; P0 resolved stays 0; the
 * route baseline is frozen unchanged.
 */
export interface TargetBReadinessSummary {
  readonly targetName: 'Target B — Production Runtime / Real Plugin Ecosystem'
  readonly readinessStatus: TargetBReadinessFlag
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
  readonly p0PendingHumanReview: 5
  readonly requiredBeforeEnable: readonly string[]
}

/** A single Target B architecture module on the status board. */
export interface TargetBArchitectureModule {
  readonly key: string
  readonly module: string
  readonly status: TargetBModuleLifecycle
  readonly enabled: false
  readonly executionCapable: false
  readonly networkCapable: false
  readonly productionCapable: false
  readonly routeImpact: 'none'
  readonly riskLevel: TargetBRiskLevel
  readonly requiredGate: string
  readonly futureImplementationNotes: string
}

/**
 * A fake, static, non-executable plugin package schema preview. Carries SHAPE
 * fields only — every value is a documentation placeholder. No real plugin file
 * is loaded, no entrypoint is executed, no registry source is fetched.
 */
export interface PluginPackageSchemaPreview {
  readonly packageId: string
  readonly version: string
  readonly descriptor: string
  readonly capabilities: readonly string[]
  readonly permissions: readonly string[]
  readonly entrypoints: readonly string[]
  readonly signature: string
  readonly publisher: string
  readonly registrySource: string
  readonly checksum: string
  readonly sandboxProfile: string
  readonly minimumHermesVersion: string
  readonly exampleOnly: true
  readonly notLoaded: true
  readonly notExecutable: true
}

/** A single permission in the plugin permission model — always denied. */
export interface TargetBPermissionEntry {
  readonly key: string
  readonly label: string
  readonly currentStatus: TargetBPermissionStatus
}

/** The frozen plugin permission model (every permission denied by default). */
export interface PluginPermissionModel {
  readonly entries: readonly TargetBPermissionEntry[]
  readonly defaultDisposition: TargetBPermissionStatus
  readonly anyGranted: false
}

/**
 * The frozen remote registry protocol preview. A documentation string uses a
 * `.invalid` domain that is never fetched. Network and fetch stay disabled;
 * signature is required; unsigned is never allowed.
 */
export interface RegistryProtocolPreview {
  readonly registryUrlExample: 'https://registry.example.invalid'
  readonly fetchEnabled: false
  readonly networkEnabled: false
  readonly trustPolicyRequired: true
  readonly signatureRequired: true
  readonly allowUnsigned: false
  readonly marketplaceEnabled: false
}

/** The frozen WebUI execution preview — visible but never executable. */
export interface WebUIExecutionPreview {
  readonly visibleInWebUI: true
  readonly executeButtonEnabled: false
  readonly approvalRequired: true
  readonly runtimeRouteAvailable: false
  readonly canSubmit: false
  readonly status: 'PREVIEW_ONLY_DISABLED'
  readonly flow: readonly TargetBExecutionFlowStep[]
}

/** A single disabled step in the projected WebUI execution flow. */
export interface TargetBExecutionFlowStep {
  readonly key: string
  readonly label: string
  readonly enabled: false
  readonly note: string
}

/**
 * The frozen approval / authorization gate model. Human approval is required,
 * no trust token is provisioned, and fake / AI / metadata approval is rejected.
 * Production authorization stays NO-GO.
 */
export interface ApprovalGateModel {
  readonly humanApprovalRequired: true
  readonly trustTokenProvisioned: false
  readonly fakeApprovalAccepted: false
  readonly aiApprovalAccepted: false
  readonly metadataApprovalAccepted: false
  readonly productionAuthorization: TargetBNoGoVerdict
}

/** A single enablement blocker (what must be done before Target B can start). */
export interface TargetBEnablementBlocker {
  readonly key: string
  readonly label: string
  readonly resolved: false
  readonly detail: string
}

/** A single Target A relationship row (how Target A relates to Target B). */
export interface TargetBTargetARelationship {
  readonly key: string
  readonly statement: string
}

/** A single Target B readiness checklist item. */
export interface TargetBReadinessCheckItem {
  readonly id: string
  readonly label: string
  readonly status: TargetBChecklistStatus
  readonly enablementBlocked: boolean
  readonly evidenceSummary: string
}

/** A read-only status chip projected into the region header (non-color text). */
export interface TargetBStatusBadge {
  readonly label: string
}

/** A frozen boundary-banner row (icon kind + explicit non-color text). */
export interface TargetBBoundaryItem {
  readonly kind: 'lock' | 'ban'
  readonly label: string
}

/** A summary card projected for the Target B readiness overview. */
export interface TargetBSummaryCard {
  readonly label: string
  readonly value: string | number
  readonly sub?: string
  readonly tone: 'ok' | 'warn' | 'danger' | 'info'
}

/** Client-side module filter keys (operate on static data only). */
export type TargetBModuleFilterKey = 'all' | TargetBModuleLifecycle

/** The full read-only Target B Readiness view model. */
export interface TargetBReadinessViewModel {
  readonly schemaVersion: typeof TARGET_B_READINESS_SCHEMA_VERSION
  readonly phase: typeof TARGET_B_READINESS_PHASE
  readonly summary: TargetBReadinessSummary
  readonly summaryCards: readonly TargetBSummaryCard[]
  readonly architectureModules: readonly TargetBArchitectureModule[]
  readonly pluginPackageSchema: PluginPackageSchemaPreview
  readonly permissionModel: PluginPermissionModel
  readonly registryProtocol: RegistryProtocolPreview
  readonly webuiExecution: WebUIExecutionPreview
  readonly approvalGate: ApprovalGateModel
  readonly enablementBlockers: readonly TargetBEnablementBlocker[]
  readonly targetARelationship: readonly TargetBTargetARelationship[]
  readonly readinessChecklist: readonly TargetBReadinessCheckItem[]
  readonly statusBadges: readonly TargetBStatusBadge[]
  readonly boundaryItems: readonly TargetBBoundaryItem[]
  readonly forbiddenActions: readonly string[]
  readonly allowedUiActions: readonly string[]
  readonly routeGovernanceBaseline: typeof TARGET_B_ROUTE_BASELINE
  readonly backendRoutesChanged: false
}
