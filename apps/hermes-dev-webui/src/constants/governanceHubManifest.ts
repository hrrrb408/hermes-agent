/**
 * Frozen static Governance Hub manifest — Phase 3L (frontend mirror).
 *
 * A tracked, reviewable, deterministic mirror of the unified read-only control
 * center state. It is the read-only data source for the Dev WebUI Governance
 * Hub section. It aggregates — read-only — the governance state already surfaced
 * by the Runtime Governance (Phase 3J) and Human Review Governance (Phase 3K)
 * sections. It carries ONLY safe, value-free fields — no API key, Authorization,
 * Bearer, secret, callable repr, shell command, SQL statement, production path,
 * local plugin path, dynamic import path, external URL, download URL, install
 * command, trust token, or real production gateway PID.
 *
 * Provenance: derived from the frozen frontend mirrors of the Phase 3 capability
 * chain:
 *   - constants/runtimeGovernanceManifest.ts       (descriptor registry, runtime,
 *     side effects, authorization verdicts, CLI examples, route baseline)
 *   - constants/humanReviewGovernanceManifest.ts   (24-gate registry, summary,
 *     evidence trail, NO-GO decisions, forbidden / allowed actions)
 *
 * The WebUI does NOT call the CLI, does NOT run the Python runtime, does NOT
 * spawn a process, does NOT fetch remote data, does NOT read or write files, and
 * does NOT access production or ~/.hermes. Every value here is static and
 * deterministic — no current time, no random id, no uuid, no network fetch.
 *
 * This manifest describes the governance state only — it never grants
 * permission, never approves a gate, never authorizes a runtime, never executes
 * a plugin, never rolls out production, and never resolves a P0 gate. resolvedCount
 * stays 0, every authorization verdict stays NO-GO / not-authorized, every route
 * count stays unchanged, and every side-effect flag stays False no matter what
 * renders.
 */

import type {
  GovernanceHubSummary,
  GovernanceModuleStatus,
  GovernanceRouteSummary,
  GovernanceProductionSafety,
  GovernanceDecisionSummary,
  GovernanceDecisionRow,
  GovernanceEvidenceSource,
  GovernanceBoundaryItem,
  GovernanceStatusBadge,
  GOVERNANCE_HUB_ROUTE_BASELINE,
  TargetACompletionSummary,
  TargetACapabilityRow,
  TargetAReadinessCheckItem,
  TargetBDeferredRow,
  TargetAReleaseReadiness,
  TargetAAcceptanceReason,
} from '@/types/api/governanceHub'

/**
 * Recursively deep-freeze a value (arrays + nested objects). Applied to every
 * exported constant so the canonical governance state is immutable at runtime —
 * an external caller can never mutate a returned projection into the canonical
 * manifest, never flip a frozen NO-GO verdict, never flip a frozen False
 * side-effect flag, and never drop a forbidden action. Reads, spreads, and
 * `.map()` copies are unaffected. Pure and total.
 */
function deepFreeze<T>(value: T): T {
  if (value === null || typeof value !== 'object') return value
  if (Array.isArray(value)) {
    for (const item of value) deepFreeze(item)
  } else {
    for (const key of Object.keys(value as Record<string, unknown>)) {
      deepFreeze((value as Record<string, unknown>)[key])
    }
  }
  return Object.freeze(value)
}

/** Schema version (mirrors GOVERNANCE_HUB_SCHEMA_VERSION). */
export const GOVERNANCE_HUB_VERSION = deepFreeze('phase-3l-governance-hub-v1')

/** Frozen route-governance baseline (unchanged by this read-only surface). */
export const GOVERNANCE_HUB_ROUTE_GOVERNANCE_BASELINE: typeof GOVERNANCE_HUB_ROUTE_BASELINE =
  '34/34/5/0/1/1'

/**
 * The conservative governance summary that tops the control center. Every
 * authorization verdict is frozen NO-GO; every P0 count is frozen; the route
 * baseline is frozen unchanged; the production gateway is frozen untouched.
 */
export const GOVERNANCE_HUB_SUMMARY: GovernanceHubSummary = deepFreeze({
  currentPhase: 'Phase 3L',
  runtimeGovernanceStatus: 'COMPLETE',
  humanReviewGovernanceStatus: 'IMPLEMENTED',
  descriptorRegistryStatus: 'IMPLEMENTED',
  runtimeCliStatus: 'COMPLETE',
  readOnlyWebuiStatus: 'COMPLETE',
  p0Total: 24,
  p0Resolved: 0,
  p0Partial: 19,
  p0PendingHumanReview: 5,
  routeGovernanceUnchanged: true,
  productionGatewayUntouched: true,
  productionRuntimeAuthorization: 'NO-GO',
  implementationAuthorization: 'NO-GO',
  productionRollout: 'NO-GO',
})

/**
 * The governance module status board (Phase 3 capability chain). Each module
 * states the phase that delivered it, a read-only evidence summary, a frozen
 * route impact (no new route), a frozen production impact (no production
 * authorization), and a frozen authorization impact (NO-GO). None of these
 * authorizes production. Two modules cross-link to an existing client-side
 * section; the Governance Hub module is itself this surface.
 */
export const GOVERNANCE_HUB_MODULES: readonly GovernanceModuleStatus[] = deepFreeze([
  {
    key: 'descriptorRegistry',
    name: 'Static Descriptor Registry',
    phase: 'Phase 3D',
    status: 'IMPLEMENTED',
    evidenceSummary:
      'Reviewed, descriptor-only plugin descriptor registry. Describes descriptors — never loads or executes a plugin.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    authorizationImpact: 'NO-GO',
    readOnly: true,
  },
  {
    key: 'safetyBaseline',
    name: 'Runtime Sandbox Safety Baseline',
    phase: 'Phase 3E-H',
    status: 'IMPLEMENTED',
    evidenceSummary:
      'Deterministic string-only evaluators for filesystem, network, production-isolation, and route-governance (34/34/5/0/1/1) boundaries.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    authorizationImpact: 'NO-GO',
    readOnly: true,
  },
  {
    key: 'sandboxProof',
    name: 'Sandbox Proof Runner',
    phase: 'Phase 3H',
    status: 'IMPLEMENTED',
    evidenceSummary:
      'Dev-only, fail-closed, in-process sandbox proof skeleton plus adversarial tests. process.spawn denied; no unapproved execution path.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    authorizationImpact: 'NO-GO',
    readOnly: true,
  },
  {
    key: 'localRuntimeMvp',
    name: 'Dev-only Local Runtime MVP',
    phase: 'Phase 3I',
    status: 'IMPLEMENTED',
    evidenceSummary:
      'Reviewed-fixture descriptor registry binds to an in-process fixture allowlist and runs fail-closed without side effects. Dev-only partial evidence.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    authorizationImpact: 'NO-GO',
    readOnly: true,
  },
  {
    key: 'runtimeExpansion',
    name: 'Runtime Fixture Expansion',
    phase: 'Phase 3I',
    status: 'IMPLEMENTED',
    evidenceSummary:
      'Multi-descriptor batch runs isolated and fail-closed; a redacted audit projects from a run / batch report without re-execution. In-memory audit only.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    authorizationImpact: 'NO-GO',
    readOnly: true,
  },
  {
    key: 'descriptorRuntimeIntegration',
    name: 'Descriptor Runtime Integration',
    phase: 'Phase 3I',
    status: 'IMPLEMENTED',
    evidenceSummary:
      'A reviewed descriptor resolves to a fixture binding through the static descriptor registry with deny-by-default provenance. No source trust granted.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    authorizationImpact: 'NO-GO',
    readOnly: true,
  },
  {
    key: 'runtimeGovernanceCli',
    name: 'Runtime Governance CLI',
    phase: 'Phase 3I',
    status: 'COMPLETE',
    evidenceSummary:
      'Read-only governance report projections: the frozen no-side-effect surface and the all-NO-GO authorization verdicts, projected without executing anything.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    authorizationImpact: 'NO-GO',
    readOnly: true,
  },
  {
    key: 'runtimeGovernanceWebui',
    name: 'Runtime Governance WebUI',
    phase: 'Phase 3J',
    status: 'COMPLETE',
    evidenceSummary:
      'Read-only descriptor registry, binding detail, P0 summary, safety matrix, and CLI examples — rendered with no execution and no new route.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    authorizationImpact: 'NO-GO',
    linkTargetSection: 'runtimeGovernance',
    readOnly: true,
  },
  {
    key: 'humanReviewWebui',
    name: 'Human Review Governance WebUI',
    phase: 'Phase 3K',
    status: 'IMPLEMENTED',
    evidenceSummary:
      'Read-only 24-gate picture (19 partial evidence, 5 pending human review), evidence trail, and frozen NO-GO decision. A decision-readiness surface only.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    authorizationImpact: 'NO-GO',
    linkTargetSection: 'humanReview',
    readOnly: true,
  },
  {
    key: 'governanceHub',
    name: 'Governance Hub',
    phase: 'Phase 3L',
    status: 'IMPLEMENTED',
    evidenceSummary:
      'This unified read-only control center. It summarizes governance state only — it executes nothing, approves nothing, authorizes nothing, and changes no route.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    authorizationImpact: 'NO-GO',
    readOnly: true,
  },
])

/**
 * The frozen route-governance projection. Exact counts (34/34/5/0/1/1); every
 * "new route" flag is frozen at 0. The Governance Hub adds no backend route.
 */
export const GOVERNANCE_HUB_ROUTE_SUMMARY: GovernanceRouteSummary = deepFreeze({
  openapiPaths: 34,
  runtimeRoutes: 34,
  toolGetRoutes: 5,
  toolWriteHttpRoutes: 0,
  toolDryRunRoutes: 1,
  toolExecutionRoutes: 1,
  newHttpRoutes: 0,
  newToolWriteRoutes: 0,
  newProviderRoutes: 0,
  newPluginRoutes: 0,
  newRuntimeRoutes: 0,
  format: '34/34/5/0/1/1',
})

/**
 * The frozen production-safety projection. Every flag is False. The exact
 * production gateway PID is deliberately NOT carried in the frontend view-model
 * (environment-specific) — the frontend states the gateway is expected unchanged
 * and untouched; the exact PID lives in docs / tests only. No live process is
 * checked from the frontend.
 */
export const GOVERNANCE_HUB_PRODUCTION_SAFETY: GovernanceProductionSafety = deepFreeze({
  productionGatewayTouched: false,
  productionGatewayExpectedUnchanged: true,
  devGatewayStarted: false,
  dashboardStarted: false,
  ports5180And5181Bound: false,
  productionHomeAccess: false,
  productionStateDbAccess: false,
  externalNetwork: false,
  realSecretRead: false,
  note:
    'Static wording only — the frontend does not inspect a live process. The ' +
    'production Gateway is expected unchanged, the Dev Gateway remains stopped, ' +
    'the Dashboard is not started, ports 5180 / 5181 remain free, and there is ' +
    'no production home access (not even metadata) and no production state ' +
    'database access.',
})

/** The frozen NO-GO decision block. Every dimension is frozen NO-GO / not-authorized. */
export const GOVERNANCE_HUB_DECISIONS: GovernanceDecisionSummary = deepFreeze({
  implementationAuthorization: 'NO-GO',
  phase3iProductionAuthorization: 'NOT_AUTHORIZED',
  productionRuntimeAuthorization: 'NO-GO',
  newBackendRoute: 'NO-GO',
  approvalBackendRoute: 'NO-GO',
  webuiExecutionRoute: 'NO-GO',
  webuiApprovalAction: 'NO-GO',
  productionRollout: 'NO-GO',
})

/**
 * The frozen decision rows rendered in the NO-GO decision panel. Each carries an
 * explicit non-color verdict and a conservative reason. Frozen so a governance
 * pass can never flip one to GO.
 */
export const GOVERNANCE_HUB_DECISION_ROWS: readonly GovernanceDecisionRow[] = deepFreeze([
  {
    key: 'implementationAuthorization',
    label: 'Implementation Authorization',
    verdict: 'NO-GO',
    reason: 'resolved_count is 0 and P0-15 (implementation authorization) is pending human review.',
  },
  {
    key: 'phase3iProductionAuthorization',
    label: 'Phase 3I Production Authorization',
    verdict: 'NOT_AUTHORIZED',
    reason: 'Dev-only fixture evidence is partial; production authorization was never granted.',
  },
  {
    key: 'productionRuntimeAuthorization',
    label: 'Production Runtime',
    verdict: 'NO-GO',
    reason: 'No approved sandbox / worker lifecycle model; P0-19 is pending human review.',
  },
  {
    key: 'newBackendRoute',
    label: 'New Backend Route',
    verdict: 'NO-GO',
    reason: 'Route baseline frozen at 34/34/5/0/1/1; no new HTTP / plugin / runtime route is added.',
  },
  {
    key: 'approvalBackendRoute',
    label: 'Approval / Authorization Backend Route',
    verdict: 'NO-GO',
    reason: 'No approve / authorize / signoff / resolve endpoint exists; P0-16 endpoint authorization is pending.',
  },
  {
    key: 'webuiExecutionRoute',
    label: 'WebUI Execution Route',
    verdict: 'NO-GO',
    reason: 'No WebUI execution / run / batch endpoint exists; no plugin is executed from the browser.',
  },
  {
    key: 'webuiApprovalAction',
    label: 'WebUI Approve / Reject / Authorize Action',
    verdict: 'NO-GO',
    reason: 'The WebUI offers no approve / reject / authorize / signoff control; metadata cannot approve a gate.',
  },
  {
    key: 'productionRollout',
    label: 'Production Rollout',
    verdict: 'NO-GO',
    reason: 'No approved rollback / incident plan; no trust token provisioned; production access forbidden.',
  },
])

/**
 * The frozen evidence trail across the Phase 3 capability chain. Each source
 * states the completed deliverable, what it proves, and — explicitly — what it
 * does NOT prove. None of these authorizes production. Phase 3L (this surface)
 * is included as a read-only summary that proves nothing more than the prior
 * partial evidence already established.
 */
export const GOVERNANCE_HUB_EVIDENCE_TRAIL: readonly GovernanceEvidenceSource[] = deepFreeze([
  {
    phase: 'Phase 3D',
    completedDeliverable: 'Static descriptor registry',
    evidenceType: 'Descriptor-only plugin descriptor registry',
    whatItProves:
      'Reviewed plugin descriptors can be described and registered statically without loading or executing any plugin.',
    whatItDoesNotProve:
      'The registry describes descriptors only. It grants no permission, loads no plugin, and executes no plugin.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
  {
    phase: 'Phase 3E-H',
    completedDeliverable: 'Runtime sandbox safety baseline',
    evidenceType: 'Static safety / route-governance baseline',
    whatItProves:
      'Deterministic string-only evaluators enforce the filesystem, network, production-isolation, and route-governance (34/34/5/0/1/1) boundaries.',
    whatItDoesNotProve:
      'It is a baseline, not an approved model. It authorizes no production runtime and grants no route exception.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
  {
    phase: 'Phase 3H',
    completedDeliverable: 'Sandbox proof runner skeleton',
    evidenceType: 'Dev-only sandbox proof skeleton + adversarial tests',
    whatItProves:
      'A fail-closed, in-process skeleton proves process.spawn is denied, the network is intent-level denied, secrets are redacted, and no unapproved execution path exists.',
    whatItDoesNotProve:
      'The skeleton is not an approved runtime sandbox, worker lifecycle, or failure-mode plan. It runs no real plugin and reads no real secret.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
  {
    phase: 'Phase 3I',
    completedDeliverable: 'Dev-only local plugin runtime MVP + expansion',
    evidenceType: 'Dev-only descriptor-backed fixture runtime',
    whatItProves:
      'A reviewed-fixture descriptor registry can bind to an in-process fixture allowlist and run fail-closed without side effects; a batch can run isolated and a redacted audit can project from a report.',
    whatItDoesNotProve:
      'Fixture execution is dev-only partial evidence. It never loads a real plugin, never reads from disk, never reaches production, and the audit is in-memory only.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
  {
    phase: 'Phase 3I',
    completedDeliverable: 'Runtime governance CLI',
    evidenceType: 'Read-only governance report projections',
    whatItProves:
      'A CLI can project the frozen no-side-effect surface and the all-NO-GO authorization verdicts without executing anything.',
    whatItDoesNotProve:
      'A governance pass authorizes nothing. It cannot approve a gate, cannot sign off, and cannot provision a trust token.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
  {
    phase: 'Phase 3J',
    completedDeliverable: 'Runtime Governance read-only WebUI',
    evidenceType: 'Read-only runtime governance WebUI surface',
    whatItProves:
      'The WebUI can render the descriptor registry, binding detail, P0 summary, and CLI examples read-only with no execution and no new route.',
    whatItDoesNotProve:
      'The WebUI is read-only evidence. It executes no runtime, loads no plugin, and adds no backend route.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
  {
    phase: 'Phase 3K',
    completedDeliverable: 'Human Review Governance read-only WebUI',
    evidenceType: 'Read-only P0 human-review / approval picture',
    whatItProves:
      'The WebUI can render the 24-gate picture (19 partial evidence, 5 pending human review), the evidence trail, and the frozen NO-GO decision read-only.',
    whatItDoesNotProve:
      'The surface is decision-readiness, not a decision. It approves no gate, resolves no P0, and provisions no trust token.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
  {
    phase: 'Phase 3L',
    completedDeliverable: 'Governance Hub unified read-only control center',
    evidenceType: 'Read-only unified governance summary',
    whatItProves:
      'The WebUI can aggregate the Runtime Governance, Human Review, route, production-safety, evidence, NO-GO, and deferred summaries into one read-only board with no execution and no new route.',
    whatItDoesNotProve:
      'The Hub is a read-only summary. It authorizes nothing, approves nothing, executes nothing, and proves nothing beyond the prior partial evidence.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
])

/**
 * The frozen deferred / still-not-authorized list. Every item remains NO-GO /
 * not-authorized and is rendered as explanatory TEXT only — never as an
 * interactive control. Frozen so a governance pass can never drop one.
 */
export const GOVERNANCE_HUB_DEFERRED_ITEMS: readonly string[] = deepFreeze([
  'production plugin runtime',
  'arbitrary plugin loading',
  'user-uploaded plugins',
  'local plugin directory loading outside fixture allowlist',
  'remote registry',
  'marketplace',
  'external plugin fetch',
  'provider-generated plugin install',
  'LLM-generated plugin install',
  'real API key reading',
  'external network',
  'new backend route',
  'approval backend route',
  'authorization backend route',
  'WebUI execution route',
  'WebUI run button',
  'WebUI approve / reject / authorize action',
  'WebUI production rollout action',
  'production rollout',
  'provider write',
  'autonomous write',
  'live provider execution',
  'shell execution',
  'database mutation outside approved tests',
  'production operation',
  'CLI input-file reading',
  'CLI output-file writing',
  'persistent runtime audit store',
])

/** Client-side cross-links to existing Dev Console sections (read-only navigation). */
export const GOVERNANCE_HUB_CROSS_LINKS = deepFreeze([
  {
    target: 'runtimeGovernance',
    label: 'View Runtime Governance',
    detail: 'Open the read-only descriptor registry, binding detail, and P0 summary (Phase 3J).',
  },
  {
    target: 'humanReview',
    label: 'View Human Review',
    detail: 'Open the read-only 24-gate human-review picture and evidence trail (Phase 3K).',
  },
] as const)

/**
 * Global actions the WebUI must NOT offer. Rendered as forbidden explanatory
 * TEXT only — never as an interactive control.
 */
export const GOVERNANCE_HUB_FORBIDDEN_ACTIONS: readonly string[] = deepFreeze([
  'approve',
  'reject',
  'authorize',
  'signoff',
  'resolve',
  'override',
  'production rollout',
  'enable production runtime',
  'enable runtime',
  'arbitrary plugin loading',
  'local plugin directory loading',
  'remote registry',
  'marketplace',
  'external plugin fetch',
  'API key entry',
  'file upload',
  'JSON execution input',
  'external network',
  'run plugin from WebUI',
  'batch execute from WebUI',
  'upload evidence',
  'load plugin',
])

/**
 * Global UI actions the read-only surface MAY offer. Every one is a harmless
 * client-only affordance that operates on static data — none calls the backend,
 * the runtime, or the CLI.
 */
export const GOVERNANCE_HUB_ALLOWED_UI_ACTIONS: readonly string[] = deepFreeze([
  'view module status board',
  'inspect module details',
  'view runtime governance section',
  'view human review section',
  'filter modules by status',
  'copy summary text',
  'read NO-GO explanation',
])

/** Frozen page-header status badges (explicit non-color text). */
export const GOVERNANCE_HUB_STATUS_BADGES: readonly GovernanceStatusBadge[] = deepFreeze([
  { label: 'READ-ONLY' },
  { label: 'UNIFIED CONTROL CENTER' },
  { label: 'NO PRODUCTION RUNTIME' },
  { label: 'NO APPROVAL ACTIONS' },
  { label: 'ROUTES UNCHANGED' },
])

/** Frozen boundary-banner rows (icon kind + explicit non-color text). */
export const GOVERNANCE_HUB_BOUNDARY_ITEMS: readonly GovernanceBoundaryItem[] = deepFreeze([
  { kind: 'lock', label: 'READ-ONLY — this page summarizes governance state only' },
  { kind: 'lock', label: 'READ-ONLY — this page cannot execute a runtime' },
  { kind: 'lock', label: 'READ-ONLY — this page cannot approve gates' },
  { kind: 'lock', label: 'READ-ONLY — this page cannot authorize production' },
  { kind: 'lock', label: 'READ-ONLY — this page cannot change routes' },
  { kind: 'ban', label: 'NO production runtime / NO production rollout' },
  { kind: 'ban', label: 'NO arbitrary plugin loading / NO local plugin directory loading' },
  { kind: 'ban', label: 'NO remote registry / NO marketplace / NO external plugin fetch' },
  { kind: 'ban', label: 'NO external network / NO real API key read' },
  { kind: 'ban', label: 'NO new backend route — route counts unchanged' },
])

// ===========================================================================
// Target A — Dev-only Runtime Prototype completion (Phase 3M).
//
// Target A is the dev-only, fixture-only, read-only-governed runtime prototype
// capability chain. It is COMPLETE in the dev-only sense ONLY: every capability
// in the chain is implemented, the governance surfaces are complete, and the
// tests are green — while production remains explicitly NO-GO. P0 resolved_count
// stays 0, five gates remain pending human review, no trust token is provisioned,
// and metadata / AI / placeholder approval cannot advance any gate.
//
// These constants are frozen, value-free, and defense-in-depth redacted (see the
// view-model redactor). They carry no secret, no Authorization / Bearer, no
// production path, no ~/.hermes path, no dynamic import path, no external URL,
// no install command, no trust token, and no real PID. Nothing here grants
// permission, loads a plugin, executes a plugin, approves a gate, authorizes a
// runtime, resolves a P0 gate, provisions a trust token, or rolls out production.
// ===========================================================================

/** Schema version (mirrors TARGET_A_SCHEMA_VERSION). */
export const TARGET_A_VERSION = deepFreeze('phase-3m-target-a-v1')

/** Frozen phase label for the Target A completion region. */
export const TARGET_A_PHASE_LABEL = deepFreeze('Phase 3M')

/**
 * The frozen Target A completion summary. `targetStatus` is COMPLETE only as a
 * dev-only prototype; production readiness is stated as NO-GO (never a
 * percentage), P0 resolved stays 0, and every production dimension stays NO-GO.
 */
export const TARGET_A_COMPLETION_SUMMARY: TargetACompletionSummary = deepFreeze({
  targetName: 'Dev-only Runtime Prototype',
  targetStatus: 'COMPLETE',
  targetScope: 'dev-only / fixture-only / read-only governed',
  completionLabel: 'Dev-only runtime prototype complete',
  completionPercentage: 100,
  productionReadiness: 'NO-GO',
  notProduction: true,
  p0Total: 24,
  p0Resolved: 0,
  p0Partial: 19,
  p0PendingHumanReview: 5,
  routeGovernance: '34/34/5/0/1/1',
  backendRouteChanges: 0,
  productionRuntime: 'NO-GO',
  webuiExecution: 'NO-GO',
  approvalActions: 'NO-GO',
  productionRollout: 'NO-GO',
  targetBStatus: 'NOT_STARTED_OR_NO_GO',
  targetBReason:
    'Production runtime and real plugin loading remain explicitly unauthorized.',
})

/**
 * The Target A capability matrix — the full Phase 3 capability chain. Every row
 * contributes to Target A; every row adds no route; every row authorizes no
 * production. The target-B impact of each is explicit (not required for Target A
 * / required for a future production phase). Frozen so a governance pass can
 * never flip a row to authorizing production.
 */
export const TARGET_A_CAPABILITY_MATRIX: readonly TargetACapabilityRow[] = deepFreeze([
  {
    capability: 'Static Descriptor Registry',
    phase: 'Phase 3D',
    status: 'IMPLEMENTED',
    evidence: 'Descriptor-only plugin descriptor registry — describes descriptors, never loads or executes a plugin.',
    tests: 'Vitest frontend + Python descriptor-registry isolation green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'complete',
    targetBImpact: 'Not required for Target A; foundation only for a future production review.',
  },
  {
    capability: 'Reviewed Fixture Descriptors',
    phase: 'Phase 3D',
    status: 'IMPLEMENTED',
    evidence: 'Reviewed fixture descriptors available in the static registry with deny-by-default provenance.',
    tests: 'Descriptor-registry validation + non-execution boundary tests green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'complete',
    targetBImpact: 'Not required for Target A.',
  },
  {
    capability: 'Sandbox Safety Baseline',
    phase: 'Phase 3E-H',
    status: 'IMPLEMENTED',
    evidence: 'Deterministic string-only evaluators for filesystem, network, production-isolation, and route-governance (34/34/5/0/1/1) boundaries.',
    tests: 'Safety baseline + route-governance regression green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'complete',
    targetBImpact: 'Baseline only — not an approved production sandbox model.',
  },
  {
    capability: 'P0 Evidence Projection',
    phase: 'Phase 3E-H',
    status: 'IMPLEMENTED',
    evidence: 'Frozen P0 evidence model: 24 gates, 0 resolved, 19 partial, 5 blocked by human review.',
    tests: 'P0 evidence isolation tests green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'complete',
    targetBImpact: 'Decision-readiness projection — not a decision.',
  },
  {
    capability: 'Proof Runner',
    phase: 'Phase 3H',
    status: 'IMPLEMENTED',
    evidence: 'Dev-only, fail-closed, in-process sandbox proof skeleton.',
    tests: 'Proof-runner skeleton tests green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'implemented',
    targetBImpact: 'Skeleton only — not an approved worker lifecycle.',
  },
  {
    capability: 'Adversarial Hardening',
    phase: 'Phase 3H',
    status: 'IMPLEMENTED',
    evidence: 'Adversarial tests prove process.spawn is denied, the network is intent-level denied, secrets are redacted, and no unapproved execution path exists.',
    tests: 'Adversarial failure-mode tests green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'implemented',
    targetBImpact: 'Hardening evidence only — not an approved runtime.',
  },
  {
    capability: 'Dev-only Fixture Runtime',
    phase: 'Phase 3I',
    status: 'IMPLEMENTED',
    evidence: 'Reviewed-fixture descriptor registry binds to an in-process fixture allowlist and runs fail-closed without side effects.',
    tests: 'Runtime MVP + fixture-runtime isolation tests green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'complete',
    targetBImpact: 'Fixture-only — never loads a real plugin, never reaches production.',
  },
  {
    capability: 'Fixture Runtime Expansion',
    phase: 'Phase 3I',
    status: 'IMPLEMENTED',
    evidence: 'Multi-descriptor batch runs isolated and fail-closed; a redacted audit projects from a run / batch report without re-execution.',
    tests: 'Runtime expansion + in-memory audit tests green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'complete',
    targetBImpact: 'In-memory audit only — no persistent runtime audit store.',
  },
  {
    capability: 'Descriptor Runtime Binding',
    phase: 'Phase 3I',
    status: 'IMPLEMENTED',
    evidence: 'A reviewed descriptor resolves to a fixture binding through the static descriptor registry with deny-by-default provenance.',
    tests: 'Descriptor runtime integration tests green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'complete',
    targetBImpact: 'No source trust granted — not a production loader.',
  },
  {
    capability: 'Runtime Governance CLI',
    phase: 'Phase 3I',
    status: 'IMPLEMENTED',
    evidence: 'Read-only governance report projections: list / show / run / batch / audit / p0-report available on the dev-only CLI.',
    tests: 'Runtime governance CLI tests green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'complete',
    targetBImpact: 'Governance report only — never approves a gate or provisions a trust token.',
  },
  {
    capability: 'Runtime Governance CLI Completion',
    phase: 'Phase 3I',
    status: 'COMPLETE',
    evidence: 'The CLI projects the frozen no-side-effect surface and the all-NO-GO authorization verdicts without executing anything.',
    tests: 'Runtime governance CLI completion tests green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'complete',
    targetBImpact: 'Not required for Target A beyond the dev-only CLI.',
  },
  {
    capability: 'Runtime Governance WebUI',
    phase: 'Phase 3J',
    status: 'COMPLETE',
    evidence: 'Read-only descriptor registry, binding detail, P0 summary, safety matrix, and CLI examples — rendered with no execution and no new route.',
    tests: 'Phase 3J frontend panel + view-model + no-leak + routes tests green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'complete',
    targetBImpact: 'Read-only evidence — not an execution surface.',
  },
  {
    capability: 'Runtime Governance WebUI QA',
    phase: 'Phase 3J',
    status: 'COMPLETE',
    evidence: 'vue-tsc type-check, ESLint, Vitest, and accessibility pass for the read-only runtime governance surface.',
    tests: 'Phase 3J completion + QA tests green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'complete',
    targetBImpact: 'QA evidence only.',
  },
  {
    capability: 'Human Review Governance WebUI',
    phase: 'Phase 3K',
    status: 'IMPLEMENTED',
    evidence: 'Read-only 24-gate picture (19 partial evidence, 5 pending human review), evidence trail, and frozen NO-GO decision.',
    tests: 'Phase 3K frontend panel + view-model + no-leak + routes tests green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'complete',
    targetBImpact: 'Decision-readiness surface — not a decision.',
  },
  {
    capability: 'Governance Hub',
    phase: 'Phase 3L',
    status: 'IMPLEMENTED',
    evidence: 'Unified read-only control center aggregating Runtime Governance, Human Review, route, production-safety, evidence, NO-GO, and deferred summaries.',
    tests: 'Phase 3L frontend panel + view-model + no-leak + routes tests green.',
    routeImpact: 'No new route',
    productionImpact: 'No production authorization',
    targetAContribution: 'complete',
    targetBImpact: 'Read-only summary — authorizes nothing.',
  },
])

/**
 * The Target A readiness checklist. Every item is pass. None says the system is
 * production-ready; production readiness remains NO-GO (stated separately).
 * Frozen so a governance pass can never flip an item to blocking or to a
 * production-readiness claim.
 */
export const TARGET_A_READINESS_CHECKLIST: readonly TargetAReadinessCheckItem[] = deepFreeze([
  {
    id: 'descriptorRegistry',
    label: 'Descriptor registry available',
    status: 'pass',
    evidenceSummary: 'Static Descriptor Registry implemented (Phase 3D).',
    linkedSection: 'governanceHub',
    blockingForTargetA: false,
  },
  {
    id: 'fixtureAllowlist',
    label: 'Fixture allowlist available',
    status: 'pass',
    evidenceSummary: 'Reviewed fixture descriptors bound to an in-process allowlist (Phase 3I).',
    blockingForTargetA: false,
  },
  {
    id: 'runtimeBinding',
    label: 'Runtime binding available',
    status: 'pass',
    evidenceSummary: 'Descriptor resolves to a fixture binding with deny-by-default provenance (Phase 3I).',
    blockingForTargetA: false,
  },
  {
    id: 'cliSurface',
    label: 'CLI list/show/run/batch/audit/p0-report available',
    status: 'pass',
    evidenceSummary: 'Runtime governance CLI complete (Phase 3I).',
    blockingForTargetA: false,
  },
  {
    id: 'runtimeGovernanceWebui',
    label: 'WebUI Runtime Governance visible',
    status: 'pass',
    evidenceSummary: 'Read-only Runtime Governance section complete (Phase 3J).',
    linkedSection: 'runtimeGovernance',
    blockingForTargetA: false,
  },
  {
    id: 'humanReviewWebui',
    label: 'WebUI Human Review Governance visible',
    status: 'pass',
    evidenceSummary: 'Read-only Human Review Governance section implemented (Phase 3K).',
    linkedSection: 'humanReview',
    blockingForTargetA: false,
  },
  {
    id: 'governanceHub',
    label: 'Governance Hub visible',
    status: 'pass',
    evidenceSummary: 'Unified read-only Governance Hub implemented (Phase 3L).',
    linkedSection: 'governanceHub',
    blockingForTargetA: false,
  },
  {
    id: 'p0Visible',
    label: 'P0 24/0/19/5 visible',
    status: 'pass',
    evidenceSummary: '24 total, 0 resolved, 19 partial, 5 pending human review — frozen and visible.',
    blockingForTargetA: false,
  },
  {
    id: 'routeGovernance',
    label: 'Route governance unchanged',
    status: 'pass',
    evidenceSummary: '34/34/5/0/1/1 — every new-route flag 0.',
    blockingForTargetA: false,
  },
  {
    id: 'productionSafety',
    label: 'Production safety unchanged',
    status: 'pass',
    evidenceSummary: 'No production gateway, state.db, home, or secret access.',
    blockingForTargetA: false,
  },
  {
    id: 'noApprovalControls',
    label: 'No approval controls',
    status: 'pass',
    evidenceSummary: 'No approve / reject / authorize / signoff / resolve / override control.',
    blockingForTargetA: false,
  },
  {
    id: 'noExecutionControls',
    label: 'No execution controls',
    status: 'pass',
    evidenceSummary: 'No run / execute / batch / WebUI execution control.',
    blockingForTargetA: false,
  },
  {
    id: 'noProductionAccess',
    label: 'No production access',
    status: 'pass',
    evidenceSummary: 'No ~/.hermes access (not even metadata), no production state.db access.',
    blockingForTargetA: false,
  },
  {
    id: 'testsGreen',
    label: 'Test suites green',
    status: 'pass',
    evidenceSummary: 'Frontend, backend isolation, CLI, descriptor, and safety tests pass.',
    blockingForTargetA: false,
  },
  {
    id: 'docsUpdated',
    label: 'Docs updated',
    status: 'pass',
    evidenceSummary: 'Phase 3M Target A completion evidence documented.',
    blockingForTargetA: false,
  },
])

/**
 * The Target B deferred matrix. Target B is the real production plugin runtime /
 * real plugin ecosystem. Every item stays NO-GO / not-authorized; each states why
 * it is deferred and what is required before it could even be considered. Frozen
 * so a governance pass can never drop or authorize one. Rendered as explanatory
 * TEXT only — never as an interactive control.
 */
export const TARGET_B_DEFERRED_MATRIX: readonly TargetBDeferredRow[] = deepFreeze([
  {
    item: 'production plugin runtime',
    currentStatus: 'NO-GO',
    whyDeferred: 'No approved sandbox / worker lifecycle model; P0-19 pending human review.',
    requiredBeforeStart: 'Approved runtime sandbox, worker lifecycle, failure-mode plan, and human signoff.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'arbitrary plugin loading',
    currentStatus: 'NO-GO',
    whyDeferred: 'Only the reviewed fixture allowlist is ever loaded.',
    requiredBeforeStart: 'A reviewed supply-chain trust model and a plugin review board.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'user-uploaded plugins',
    currentStatus: 'NO-GO',
    whyDeferred: 'No upload surface exists; uploads are explicitly forbidden.',
    requiredBeforeStart: 'A signed, reviewed upload pipeline and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'local plugin directory loading outside fixture allowlist',
    currentStatus: 'NO-GO',
    whyDeferred: 'Only the fixture allowlist binds; directory scanning is forbidden.',
    requiredBeforeStart: 'A reviewed directory-trust policy and allowlist governance.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'remote registry',
    currentStatus: 'NO-GO',
    whyDeferred: 'No remote registry integration exists or is reachable.',
    requiredBeforeStart: 'A pinned, signed registry and an external-network review.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'marketplace',
    currentStatus: 'NO-GO',
    whyDeferred: 'No marketplace integration exists.',
    requiredBeforeStart: 'A reviewed marketplace trust model and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'external plugin fetch',
    currentStatus: 'NO-GO',
    whyDeferred: 'No external fetch path exists; external network is forbidden.',
    requiredBeforeStart: 'An external-network allowlist review and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'provider-generated plugin install',
    currentStatus: 'NO-GO',
    whyDeferred: 'Providers cannot install plugins.',
    requiredBeforeStart: 'A provider-trust model and a human review board.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'LLM-generated plugin install',
    currentStatus: 'NO-GO',
    whyDeferred: 'LLM-generated installs are explicitly forbidden.',
    requiredBeforeStart: 'A review board for generated plugins; never AI-only approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'real API key reading',
    currentStatus: 'NO-GO',
    whyDeferred: 'The surface reads no real API key; secrets are redacted.',
    requiredBeforeStart: 'A secret-read policy and an approved secret store.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'external network',
    currentStatus: 'NO-GO',
    whyDeferred: 'No outbound network path exists.',
    requiredBeforeStart: 'An external-network allowlist review and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'new backend route',
    currentStatus: 'NO-GO',
    whyDeferred: 'Route baseline frozen at 34/34/5/0/1/1; no route added.',
    requiredBeforeStart: 'A route-governance review and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'approval backend route',
    currentStatus: 'NO-GO',
    whyDeferred: 'No approve endpoint exists; P0-16 pending human review.',
    requiredBeforeStart: 'An endpoint-authorization review and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'authorization backend route',
    currentStatus: 'NO-GO',
    whyDeferred: 'No authorize / signoff endpoint exists.',
    requiredBeforeStart: 'An authorization-endpoint review and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'WebUI execution route',
    currentStatus: 'NO-GO',
    whyDeferred: 'No WebUI execution / run / batch endpoint exists.',
    requiredBeforeStart: 'An execution-route review and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'WebUI run button',
    currentStatus: 'NO-GO',
    whyDeferred: 'No run control is offered from the browser.',
    requiredBeforeStart: 'An execution-control review and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'WebUI approve / reject / authorize action',
    currentStatus: 'NO-GO',
    whyDeferred: 'The WebUI offers no approval control; metadata cannot approve a gate.',
    requiredBeforeStart: 'An approval-action review and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'WebUI production rollout action',
    currentStatus: 'NO-GO',
    whyDeferred: 'No rollout control exists; no trust token provisioned.',
    requiredBeforeStart: 'A rollout / rollback / incident plan and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'production rollout',
    currentStatus: 'NO-GO',
    whyDeferred: 'No approved rollback / incident plan; production access forbidden.',
    requiredBeforeStart: 'A rollback / incident plan, a trust token, and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'provider write',
    currentStatus: 'NO-GO',
    whyDeferred: 'Providers cannot perform writes.',
    requiredBeforeStart: 'A provider-write policy and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'autonomous write',
    currentStatus: 'NO-GO',
    whyDeferred: 'Autonomous writes are explicitly forbidden.',
    requiredBeforeStart: 'An autonomous-write policy and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'live provider execution',
    currentStatus: 'NO-GO',
    whyDeferred: 'Only dev-only fixture execution exists; no live provider execution.',
    requiredBeforeStart: 'A live-execution review and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'shell execution',
    currentStatus: 'NO-GO',
    whyDeferred: 'process.spawn is denied; no shell execution path exists.',
    requiredBeforeStart: 'A shell-execution review and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'database mutation outside approved tests',
    currentStatus: 'NO-GO',
    whyDeferred: 'No production database mutation; only approved test fixtures mutate.',
    requiredBeforeStart: 'A database-mutation policy and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'production operation',
    currentStatus: 'NO-GO',
    whyDeferred: 'No production operation of any kind.',
    requiredBeforeStart: 'A production-operation review and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'CLI input-file reading',
    currentStatus: 'NO-GO',
    whyDeferred: 'The CLI does not read input files.',
    requiredBeforeStart: 'An input-file review and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'CLI output-file writing',
    currentStatus: 'NO-GO',
    whyDeferred: 'The CLI does not write output files.',
    requiredBeforeStart: 'An output-file review and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
  {
    item: 'persistent runtime audit store',
    currentStatus: 'NO-GO',
    whyDeferred: 'Only an in-memory audit projects from a report; no persistent store.',
    requiredBeforeStart: 'A persistent-audit review and human approval.',
    targetAImpact: 'not required',
    targetBImpact: 'required / future phase',
  },
])

/** The frozen Target A release-readiness projection. No value implies production. */
export const TARGET_A_RELEASE_READINESS: TargetAReleaseReadiness = deepFreeze({
  frontendTests: 'green',
  backendIsolationTests: 'green',
  runtimeCliTests: 'green',
  descriptorRegistryTests: 'green',
  memoryCheck: 'PASS',
  routeGovernance: 'unchanged',
  productionSafety: 'unchanged',
  worktreeExpectedCleanAfterCommit: true,
  claudeTracked: false,
})

/**
 * The final dev-only prototype acceptance reasoning. `verdict` is PASS in the
 * dev-only sense ONLY — the whyPass list states the prototype is complete, the
 * whyNotProduction list states explicitly why this is NOT production
 * authorization. Frozen so a governance pass can never flip the verdict or drop a
 * not-production reason.
 */
export const TARGET_A_ACCEPTANCE: TargetAAcceptanceReason = deepFreeze({
  verdict: 'PASS',
  whyPass: [
    'All Target A capabilities in the capability chain are implemented.',
    'The read-only governance surfaces (Runtime Governance, Human Review, Governance Hub) are complete.',
    'Frontend, backend isolation, CLI, descriptor, and safety test suites are green.',
    'Route governance is unchanged (34/34/5/0/1/1).',
    'Production is untouched — no gateway, state.db, home, or secret access.',
  ],
  whyNotProduction: [
    'P0 resolved_count remains 0.',
    'Five gates remain pending human review (P0-15 / P0-16 / P0-18 / P0-19 / P0-22).',
    'Production runtime remains NO-GO.',
    'No trust token is provisioned.',
    'No production rollout authorization exists.',
  ],
})

/**
 * The Target A completed boundary — what Target A delivers (dev-only). Rendered as
 * explanatory TEXT only.
 */
export const TARGET_A_BOUNDARY_COMPLETED: readonly string[] = deepFreeze([
  'dev-only fixture runtime',
  'static descriptor registry',
  'CLI',
  'read-only WebUI governance',
  'human review read-only visibility',
  'governance hub',
  'tests / evidence',
])

/**
 * The Target B deferred boundary — what remains NO-GO / not started. Rendered as
 * explanatory TEXT only — never as an interactive control.
 */
export const TARGET_A_BOUNDARY_DEFERRED: readonly string[] = deepFreeze([
  'production runtime',
  'arbitrary plugin loading',
  'real plugin ecosystem',
  'remote registry',
  'marketplace',
  'external network',
  'real API keys',
  'WebUI execution',
  'production rollout',
])
