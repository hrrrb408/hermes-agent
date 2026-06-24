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
