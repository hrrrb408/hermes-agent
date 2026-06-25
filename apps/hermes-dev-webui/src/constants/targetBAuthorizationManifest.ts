/**
 * Frozen static Target B Authorization Package manifest — Phase 4C (frontend mirror).
 *
 * A tracked, reviewable, deterministic mirror of the **Target B Authorization &
 * Gate Resolution Package** state. Phase 4C builds the **authorization-material
 * validation structure** on top of the Phase 4B gated engineering layers: the
 * human approval record schema, the trust token validation pipeline, the trusted
 * publisher set, the production signature verifier authorization adapter, the
 * sandbox worker lifecycle approval, the registry trust policy approval, the
 * network allowlist, the secret handling policy, the rollback / incident plan
 * approval, the route authorization plan, the P0 pending-gate resolution
 * evaluator, and the unified enablement readiness evaluator.
 *
 * This manifest carries ONLY safe, value-free, fail-closed fields — no API key,
 * Authorization, Bearer, secret, callable repr, shell command, SQL statement,
 * production path, local plugin path, dynamic import path, executable
 * entrypoint, real external URL, download URL, install command, real registry
 * token, real trust token, real plugin signature, or production home path.
 *
 * Provenance: derived from the frozen backend Phase 4C authorization layers in
 *   - hermes_cli/dev_web_target_b_authorization_common.py   (shared common)
 *   - hermes_cli/dev_web_target_b_human_approval.py          (human approval schema)
 *   - hermes_cli/dev_web_target_b_trust_token.py             (trust token validation)
 *   - hermes_cli/dev_web_target_b_trusted_publishers.py      (trusted publisher set)
 *   - hermes_cli/dev_web_target_b_production_signature.py    (production signature verifier)
 *   - hermes_cli/dev_web_target_b_sandbox_lifecycle.py       (sandbox worker lifecycle)
 *   - hermes_cli/dev_web_target_b_registry_policy.py         (registry trust policy)
 *   - hermes_cli/dev_web_target_b_network_policy.py          (network allowlist)
 *   - hermes_cli/dev_web_target_b_secret_policy.py           (secret handling policy)
 *   - hermes_cli/dev_web_target_b_incident_rollback.py       (rollback / incident plan)
 *   - hermes_cli/dev_web_target_b_route_authorization.py     (route authorization plan)
 *   - hermes_cli/dev_web_target_b_p0_gate_resolution.py      (P0 gate resolution)
 *   - hermes_cli/dev_web_target_b_enablement_readiness.py    (enablement readiness)
 *
 * The WebUI does NOT call the CLI, does NOT run the Python runtime, does NOT
 * spawn a process, does NOT fetch a remote registry, does NOT open a
 * marketplace, does NOT load a plugin, does NOT read or write files, does NOT
 * access production or the production home, and does NOT provision a trust
 * token. Every value here is static and deterministic — no current time, no
 * random id, no uuid, no network fetch.
 *
 * This manifest describes the authorization-material validation structure ONLY
 * — it never fabricates an approval, never bypasses P0, never mints a trust
 * token, never treats metadata / a static manifest / an AI approval as
 * authorization, never flips the production runtime to GO, never provisions a
 * trust token, never authorizes a signature verifier, never enables a sandbox
 * worker, never opens a registry, never opens a marketplace, never reads a real
 * API key, never authorizes a route, and never resolves a P0 gate. The readiness
 * status stays BLOCKED, every authorization verdict stays NO-GO, the trust token
 * stays not provisioned, P0 resolved stays 0, and the route baseline stays
 * unchanged (34/34/5/0/1/1) no matter what renders.
 */

import type {
  TargetBAuthorizationSummary,
  TargetBAuthorizationLayer,
  TargetBHumanApprovalProjection,
  TargetBTrustTokenProjection,
  TargetBTrustedPublisherProjection,
  TargetBProductionSignatureProjection,
  TargetBSandboxLifecycleProjection,
  TargetBPolicyProjection,
  TargetBRollbackIncidentProjection,
  TargetBRouteAuthorizationProjection,
  TargetBP0GateCoverageRow,
  TargetBP0GateCoverageProjection,
  TargetBEnablementReadinessProjection,
  TargetBAuthorizationBlocker,
  TargetBAuthorizationStatusBadge,
  TargetBAuthorizationBoundaryItem,
  TARGET_B_AUTHORIZATION_ROUTE_BASELINE,
} from '@/types/api/targetBAuthorization'

/**
 * Recursively deep-freeze a value (arrays + nested objects). Applied to every
 * exported constant so the canonical authorization state is immutable at
 * runtime — an external caller can never mutate a returned projection into the
 * canonical manifest, never flip a frozen BLOCKED readiness, never flip a frozen
 * NO-GO verdict, never flip a frozen false authorization flag, never provision a
 * trust token, and never raise P0 resolved above 0.
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

/** Schema version (mirrors TARGET_B_AUTHORIZATION_SCHEMA_VERSION). */
export const TARGET_B_AUTHORIZATION_VERSION = deepFreeze('phase-4c-target-b-authorization-v1')

/** Frozen phase label for the Target B authorization region. */
export const TARGET_B_AUTHORIZATION_PHASE_LABEL = deepFreeze('Phase 4C')

/** Frozen route-governance baseline (unchanged by this read-only surface). */
export const TARGET_B_AUTHORIZATION_ROUTE_GOVERNANCE_BASELINE: typeof TARGET_B_AUTHORIZATION_ROUTE_BASELINE =
  '34/34/5/0/1/1'

/**
 * The conservative Target B authorization package summary. The readiness status
 * is BLOCKED (no real approval / trust token exists); production enablement is
 * not allowed; every authorization verdict is NO-GO; the trust token is not
 * provisioned; the production signature verifier is not authorized; P0 resolved
 * stays 0; the route baseline is unchanged.
 */
export const TARGET_B_AUTHORIZATION_SUMMARY: TargetBAuthorizationSummary = deepFreeze({
  targetName: 'Target B — Production Runtime / Real Plugin Ecosystem',
  authorizationStatus: 'AUTHORIZATION_PACKAGE_IMPLEMENTED',
  readinessStatus: 'BLOCKED',
  productionEnablementAllowed: false,
  productionRuntime: 'NO-GO',
  registry: 'NO-GO',
  marketplace: 'NO-GO',
  webuiExecution: 'NO-GO',
  approvalAuthorization: 'NO-GO',
  productionRollout: 'NO-GO',
  trustTokenProvisioned: false,
  productionSignatureVerifierAuthorized: false,
  p0Total: 24,
  p0Resolved: 0,
  p0PartialEvidence: 19,
  p0PendingHumanReview: 5,
  pendingHumanReviewGates: ['P0-15', 'P0-16', 'P0-18', 'P0-19', 'P0-22'],
  requiredBeforeEnable: [
    'real out-of-band human approval',
    'real out-of-band trust token',
    'trusted publisher set',
    'production signature verifier authorization',
    'sandbox worker lifecycle approval',
    'registry trust policy approval',
    'network allowlist approval',
    'secret handling policy approval',
    'rollback / incident plan approval',
    'route authorization approval',
    'P0 gate resolution',
  ],
})

/**
 * The Target B authorization sub-layer board. Eleven independent authorization
 * sub-layers — every one is NOT_AUTHORIZED (one is DESIGN_READY_ONLY) — each
 * states the real authorization material it would require. Frozen so a
 * governance pass can never flip a capability.
 */
export const TARGET_B_AUTHORIZATION_LAYERS: readonly TargetBAuthorizationLayer[] = deepFreeze([
  {
    key: 'humanApproval',
    layer: 'Human Approval Record Schema',
    status: 'NOT_AUTHORIZED',
    authorized: false,
    fixtureOnly: false,
    riskLevel: 'critical',
    requiredMaterial: 'real out-of-band human approval (P0-15 / P0-22)',
  },
  {
    key: 'trustToken',
    layer: 'Trust Token Validation',
    status: 'NOT_AUTHORIZED',
    authorized: false,
    fixtureOnly: false,
    riskLevel: 'critical',
    requiredMaterial: 'real out-of-band trust token',
  },
  {
    key: 'trustedPublishers',
    layer: 'Trusted Publisher Set',
    status: 'NOT_AUTHORIZED',
    authorized: false,
    fixtureOnly: false,
    riskLevel: 'high',
    requiredMaterial: 'reviewed trusted publisher set',
  },
  {
    key: 'productionSignature',
    layer: 'Production Signature Verifier Authorization',
    status: 'NOT_AUTHORIZED',
    authorized: false,
    fixtureOnly: true,
    riskLevel: 'critical',
    requiredMaterial: 'real signing key + trust policy',
  },
  {
    key: 'sandboxLifecycle',
    layer: 'Sandbox Worker Lifecycle Approval',
    status: 'NOT_AUTHORIZED',
    authorized: false,
    fixtureOnly: false,
    riskLevel: 'critical',
    requiredMaterial: 'approved sandbox / worker lifecycle (P0-19)',
  },
  {
    key: 'registryPolicy',
    layer: 'Registry Trust Policy Approval',
    status: 'NOT_AUTHORIZED',
    authorized: false,
    fixtureOnly: false,
    riskLevel: 'critical',
    requiredMaterial: 'reviewed registry trust policy + network review',
  },
  {
    key: 'networkPolicy',
    layer: 'Network Allowlist Policy',
    status: 'NOT_AUTHORIZED',
    authorized: false,
    fixtureOnly: false,
    riskLevel: 'critical',
    requiredMaterial: 'approved external-network allowlist',
  },
  {
    key: 'secretPolicy',
    layer: 'Secret Handling Policy',
    status: 'NOT_AUTHORIZED',
    authorized: false,
    fixtureOnly: false,
    riskLevel: 'critical',
    requiredMaterial: 'approved secret-handling policy',
  },
  {
    key: 'incidentRollback',
    layer: 'Rollback / Incident Plan Approval',
    status: 'DESIGN_READY_ONLY',
    authorized: false,
    fixtureOnly: false,
    riskLevel: 'high',
    requiredMaterial: 'approved rollback / incident plan (P0-21 / P0-23)',
  },
  {
    key: 'routeAuthorization',
    layer: 'Route Authorization Plan',
    status: 'NOT_AUTHORIZED',
    authorized: false,
    fixtureOnly: false,
    riskLevel: 'high',
    requiredMaterial: 'approved route-governance authorization',
  },
  {
    key: 'p0GateResolution',
    layer: 'P0 Gate Resolution Evaluator',
    status: 'NOT_AUTHORIZED',
    authorized: false,
    fixtureOnly: false,
    riskLevel: 'critical',
    requiredMaterial: 'real human approval + trust token + evidence',
  },
])

/** The frozen human approval gate projection. */
export const TARGET_B_HUMAN_APPROVAL: TargetBHumanApprovalProjection = deepFreeze({
  approvalPresent: false,
  valid: false,
  productionValid: false,
  fakeApprovalRejected: true,
  aiApprovalRejected: true,
  metadataApprovalRejected: true,
  staticManifestRejected: true,
  fixtureOnlyNeverProduction: true,
  requiredGateCoverage: ['P0-15', 'P0-16', 'P0-18', 'P0-19', 'P0-22'],
  productionAuthorization: 'NO-GO',
})

/** The frozen trust token validation projection. */
export const TARGET_B_TRUST_TOKEN: TargetBTrustTokenProjection = deepFreeze({
  provisioned: false,
  valid: false,
  productionAuthorized: false,
  fakeTokenRejected: true,
  aiTokenRejected: true,
  metadataTokenRejected: true,
  noSecretRead: true,
  noProductionHomeAccess: true,
  productionAuthorization: 'NO-GO',
})

/** The frozen trusted publisher set projection. */
export const TARGET_B_TRUSTED_PUBLISHERS: TargetBTrustedPublisherProjection = deepFreeze({
  trustedPublishersCount: 0,
  unknownPublisherRejected: true,
  marketplacePublisherRejected: true,
  unsignedPublisherRejected: true,
  wildcardPublisherRejected: true,
  overbroadPermissionsRejected: true,
  productionAuthorization: 'NO-GO',
})

/** The frozen production signature verifier authorization projection. */
export const TARGET_B_PRODUCTION_SIGNATURE: TargetBProductionSignatureProjection = deepFreeze({
  verifierInterfaceImplemented: true,
  productionVerifierAuthorized: false,
  fixtureVerifierOnly: true,
  realVerificationEnabled: false,
  fixtureSignatureDoesNotImplyProduction: true,
  forgedSignatureRejected: true,
  unknownPublisherRejected: true,
  mismatchedChecksumRejected: true,
  productionAuthorization: 'NO-GO',
})

/** The frozen sandbox worker lifecycle approval projection. */
export const TARGET_B_SANDBOX_LIFECYCLE: TargetBSandboxLifecycleProjection = deepFreeze({
  lifecycleApproved: false,
  workerStartAllowed: false,
  processSpawnAllowed: false,
  networkAllowed: false,
  filesystemWriteAllowed: false,
  secretsAllowed: false,
  killSwitchArmed: false,
  productionGatewayUntouched: true,
  productionAuthorization: 'NO-GO',
})

/** The frozen registry / network / secret policy projection. */
export const TARGET_B_POLICIES: TargetBPolicyProjection = deepFreeze({
  registryDisabled: true,
  registryFetchAllowed: false,
  marketplaceAllowed: false,
  wildcardDomainsRejected: true,
  networkAllowlistPresent: false,
  networkDestinationsAllowed: 0,
  wildcardHostsDenied: true,
  cleartextHttpDenied: true,
  noSocketOpened: true,
  secretPolicyDefaultDeny: true,
  secretValuesRedacted: true,
  noSecretRead: true,
  productionAuthorization: 'NO-GO',
})

/** The frozen rollback / incident plan approval projection. */
export const TARGET_B_ROLLBACK_INCIDENT: TargetBRollbackIncidentProjection = deepFreeze({
  rollbackPlanPresent: true,
  rollbackPlanApproved: false,
  incidentPlanApproved: false,
  killSwitchReady: 'DESIGN_READY_ONLY',
  productionRollbackAuthorized: false,
  productionRollout: 'NO-GO',
  productionGatewayUntouched: true,
  productionAuthorization: 'NO-GO',
})

/** The frozen route authorization plan projection. */
export const TARGET_B_ROUTE_AUTHORIZATION: TargetBRouteAuthorizationProjection = deepFreeze({
  routeAuthorized: false,
  proposedRoutesCount: 4,
  proposedRoutesRegistered: 0,
  openapiDelta: 0,
  runtimeRouteDelta: 0,
  routeGovernanceBaseline: '34/34/5/0/1/1',
  backendRoutesChanged: false,
  productionAuthorization: 'NO-GO',
})

/** The frozen P0 gate coverage rows (5 pending gates, every one unresolved). */
export const TARGET_B_P0_GATE_COVERAGE_ROWS: readonly TargetBP0GateCoverageRow[] = deepFreeze([
  { gateId: 'P0-15', resolved: false, hasEvidence: true, hasHumanApproval: false, hasTrustToken: false },
  { gateId: 'P0-16', resolved: false, hasEvidence: true, hasHumanApproval: false, hasTrustToken: false },
  { gateId: 'P0-18', resolved: false, hasEvidence: true, hasHumanApproval: false, hasTrustToken: false },
  { gateId: 'P0-19', resolved: false, hasEvidence: true, hasHumanApproval: false, hasTrustToken: false },
  { gateId: 'P0-22', resolved: false, hasEvidence: true, hasHumanApproval: false, hasTrustToken: false },
])

/** The frozen P0 gate coverage projection. */
export const TARGET_B_P0_GATE_COVERAGE: TargetBP0GateCoverageProjection = deepFreeze({
  p0Total: 24,
  p0Resolved: 0,
  p0PartialEvidence: 19,
  pendingHumanReview: 5,
  pendingHumanReviewGates: ['P0-15', 'P0-16', 'P0-18', 'P0-19', 'P0-22'],
  resolvedCountDelta: 0,
  coverage: TARGET_B_P0_GATE_COVERAGE_ROWS,
  productionAuthorization: 'NO-GO',
})

/** The frozen enablement readiness projection. */
export const TARGET_B_ENABLEMENT_READINESS: TargetBEnablementReadinessProjection = deepFreeze({
  readinessStatus: 'BLOCKED',
  productionEnablementAllowed: false,
  allGatesPass: false,
  fixtureOnly: false,
  blockers: [
    'human_approval_missing',
    'trust_token_not_provisioned',
    'trusted_publisher_set_empty',
    'production_signature_verifier_not_authorized',
    'sandbox_lifecycle_not_approved',
    'registry_trust_policy_not_approved',
    'network_allowlist_not_approved',
    'secret_policy_default_deny',
    'incident_rollback_plan_not_approved',
    'route_authorization_not_approved',
    'p0_gates_not_resolved',
  ],
  productionAuthorization: 'NO-GO',
})

/**
 * The enablement blockers — what real authorization material must exist before
 * Target B could even be considered. Every blocker stays unresolved (resolved
 * false). Frozen so a governance pass can never silently resolve one.
 */
export const TARGET_B_AUTHORIZATION_BLOCKERS: readonly TargetBAuthorizationBlocker[] = deepFreeze([
  { key: 'humanApproval', label: 'Out-of-band human approval', resolved: false, detail: 'A signed human approval covering P0-15 / P0-16 / P0-18 / P0-19 / P0-22 is required; none exists. Fake / AI / metadata / static approvals are rejected.' },
  { key: 'trustToken', label: 'Trust token', resolved: false, detail: 'No out-of-band trust token is provisioned; a smuggled fake token cannot mint one.' },
  { key: 'trustedPublishers', label: 'Trusted publisher set', resolved: false, detail: 'The production trusted publisher set is empty; unknown / marketplace / unsigned / wildcard publishers are rejected.' },
  { key: 'productionSignature', label: 'Production signature verifier', resolved: false, detail: 'The verifier interface is implemented; the production verifier is not authorized (fixture-only). A valid fixture signature does not imply production authorization.' },
  { key: 'sandboxLifecycle', label: 'Sandbox worker lifecycle', resolved: false, detail: 'No approved production sandbox / worker lifecycle; no worker start, no process spawn, no network, no filesystem write, no secrets.' },
  { key: 'registryPolicy', label: 'Registry trust policy', resolved: false, detail: 'The registry is disabled; no reviewed, pinned, signed registry exists. No fetch, no marketplace.' },
  { key: 'networkPolicy', label: 'Network allowlist', resolved: false, detail: 'No external-network allowlist review; default deny, wildcard hosts denied, cleartext HTTP denied.' },
  { key: 'secretPolicy', label: 'Secret handling policy', resolved: false, detail: 'No approved secret-handling policy; default deny, no real API key read, secret values redacted.' },
  { key: 'incidentRollback', label: 'Rollback / incident plan', resolved: false, detail: 'The kill switch is design-ready only; no approved rollback / incident plan; production rollout stays NO-GO.' },
  { key: 'routeAuthorization', label: 'Route authorization', resolved: false, detail: 'No route-governance authorization; proposed routes stay disabled; route counts unchanged (34/34/5/0/1/1).' },
  { key: 'p0Gates', label: 'P0 gate resolution', resolved: false, detail: '24 P0 gates, 0 resolved; P0-15 / P0-16 / P0-18 / P0-19 / P0-22 require a real human approval + trust token + evidence.' },
])

/** Frozen page-header status badges (explicit non-color text). */
export const TARGET_B_AUTHORIZATION_STATUS_BADGES: readonly TargetBAuthorizationStatusBadge[] = deepFreeze([
  { label: 'AUTHORIZATION PACKAGE' },
  { label: 'READINESS BLOCKED' },
  { label: 'PRODUCTION NO-GO' },
  { label: 'TRUST TOKEN NOT PROVISIONED' },
  { label: 'WEBUI EXECUTION DISABLED' },
  { label: 'REGISTRY DISABLED' },
  { label: 'MARKETPLACE DISABLED' },
  { label: 'P0 RESOLVED 0' },
])

/** Frozen boundary-banner rows (icon kind + explicit non-color text). */
export const TARGET_B_AUTHORIZATION_BOUNDARY_ITEMS: readonly TargetBAuthorizationBoundaryItem[] = deepFreeze([
  { kind: 'lock', label: 'AUTHORIZATION PACKAGE — validation structure implemented, every gate fail-closed' },
  { kind: 'ban', label: 'NO fabricated approval / NO AI approval / NO metadata approval / NO static-manifest approval' },
  { kind: 'ban', label: 'NO trust token provisioned / NO fake token accepted' },
  { kind: 'ban', label: 'NO production signature verifier authorized (fixture-only)' },
  { kind: 'ban', label: 'NO sandbox worker start / NO process spawn / NO network / NO secrets' },
  { kind: 'ban', label: 'NO registry fetch / NO marketplace / NO external network / NO socket' },
  { kind: 'ban', label: 'NO real API key read / NO secret read / NO production home access' },
  { kind: 'ban', label: 'NO production rollout / NO production rollback authorization' },
  { kind: 'ban', label: 'NO route authorized / NO new backend route — route counts unchanged' },
  { kind: 'ban', label: 'NO P0 gate resolved — P0 resolved stays 0' },
])

/**
 * Global actions the WebUI must NOT offer on this surface. Rendered as
 * forbidden explanatory TEXT only — never as an interactive control.
 */
export const TARGET_B_AUTHORIZATION_FORBIDDEN_ACTIONS: readonly string[] = deepFreeze([
  'approve',
  'reject',
  'authorize',
  'signoff',
  'resolve',
  'override',
  'provision trust token',
  'upload approval',
  'production rollout',
  'enable production runtime',
  'enable runtime',
  'start worker',
  'fetch registry',
  'marketplace',
  'external network',
  'real API key entry',
  'secret input',
  'file upload',
  'JSON execution input',
  'run plugin from WebUI',
])

/**
 * Global UI actions the read-only surface MAY offer. Every one is a harmless
 * client-only affordance that operates on static data — none calls the backend,
 * the runtime, the CLI, or the network.
 */
export const TARGET_B_AUTHORIZATION_ALLOWED_UI_ACTIONS: readonly string[] = deepFreeze([
  'inspect authorization layer',
  'filter authorization layers',
  'copy authorization summary',
  'view Target A region',
  'view Target B readiness region',
  'view Target B implementation region',
  'view Human Review section',
  'view Runtime Governance section',
  'read BLOCKED explanation',
])
