/**
 * Frozen static Target B Implementation manifest — Phase 4B (frontend mirror).
 *
 * A tracked, reviewable, deterministic mirror of the **Target B end-to-end
 * implementation** state. Target B is the long-term goal of opening a real
 * production plugin runtime. Phase 4B implements the **full engineering path** —
 * the signed package schema, the signature verifier interface, the permission /
 * capability model, the registry trust policy, the sandbox broker, the
 * execution policy gate, the approval / authorization gate, the runtime
 * orchestrator, the audit trail, and the rollback / kill switch — while keeping
 * **every capability gated and disabled**.
 *
 * This manifest carries ONLY safe, value-free, disabled fields — no API key,
 * Authorization, Bearer, secret, callable repr, shell command, SQL statement,
 * production path, local plugin path, dynamic import path, executable
 * entrypoint, real external URL, download URL, install command, real registry
 * token, real plugin signature, or production home path.
 *
 * Provenance: derived from the frozen backend gated implementation layers in
 *   - hermes_cli/dev_web_target_b_report.py         (aggregate gated report)
 *   - hermes_cli/dev_web_target_b_package.py         (signed package schema)
 *   - hermes_cli/dev_web_target_b_signature.py       (signature verifier)
 *   - hermes_cli/dev_web_target_b_permissions.py     (permission / capability model)
 *   - hermes_cli/dev_web_target_b_registry.py        (registry trust policy)
 *   - hermes_cli/dev_web_target_b_sandbox.py         (sandbox broker)
 *   - hermes_cli/dev_web_target_b_approval.py        (approval / authorization gate)
 *   - hermes_cli/dev_web_target_b_execution_policy.py(execution policy gate)
 *   - hermes_cli/dev_web_target_b_runtime.py         (runtime orchestrator)
 *   - hermes_cli/dev_web_target_b_audit.py           (audit trail)
 *   - hermes_cli/dev_web_target_b_rollback.py        (rollback / kill switch)
 *   - hermes_cli/dev_web_p0_evidence.py              (P0 gates, frozen NO-GO)
 *   - hermes_cli/dev_web_safety_baseline.py          (route-governance 34/34/5/0/1/1)
 *
 * The WebUI does NOT call the CLI, does NOT run the Python runtime, does NOT
 * spawn a process, does NOT fetch a remote registry, does NOT open a
 * marketplace, does NOT load a plugin, does NOT read or write files, and does
 * NOT access production or the production home. Every value here is static and
 * deterministic — no current time, no random id, no uuid, no network fetch.
 *
 * This manifest describes the gated implementation ONLY — it never grants
 * permission, never loads a plugin, never executes a plugin, never fetches a
 * registry, never opens a marketplace, never reads a real API key, never
 * provisions a trust token, never approves a gate, never authorizes a runtime,
 * and never resolves a P0 gate. Execution stays DISABLED, every authorization
 * verdict stays NO-GO, every permission stays DENIED_BY_DEFAULT, and P0
 * resolved stays 0 no matter what renders.
 */

import type {
  TargetBImplementationSummary,
  TargetBImplementationLayer,
  TargetBPackageSchemaPreview,
  TargetBImplementationPermissionEntry,
  TargetBImplementationPermissionModel,
  TargetBCapabilityEntry,
  TargetBCapabilityModel,
  TargetBSignatureVerificationProjection,
  TargetBRegistryTrustProjection,
  TargetBSandboxBrokerProjection,
  TargetBApprovalGateProjection,
  TargetBExecutionPolicyProjection,
  TargetBAuditRollbackProjection,
  TargetBImplementationBlocker,
  TargetBImplementationStatusBadge,
  TargetBImplementationBoundaryItem,
  TARGET_B_IMPLEMENTATION_ROUTE_BASELINE,
} from '@/types/api/targetBImplementation'

/**
 * Recursively deep-freeze a value (arrays + nested objects). Applied to every
 * exported constant so the canonical implementation state is immutable at
 * runtime — an external caller can never mutate a returned projection into the
 * canonical manifest, never flip a frozen NO-GO verdict, never flip a frozen
 * disabled capability, never flip a frozen DENIED_BY_DEFAULT permission, never
 * flip a frozen false execution flag, and never raise P0 resolved above 0.
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

/** Schema version (mirrors TARGET_B_IMPLEMENTATION_SCHEMA_VERSION). */
export const TARGET_B_IMPLEMENTATION_VERSION = deepFreeze('phase-4b-target-b-implementation-v1')

/** Frozen phase label for the Target B implementation region. */
export const TARGET_B_IMPLEMENTATION_PHASE_LABEL = deepFreeze('Phase 4B')

/** Frozen route-governance baseline (unchanged by this read-only surface). */
export const TARGET_B_IMPLEMENTATION_ROUTE_GOVERNANCE_BASELINE: typeof TARGET_B_IMPLEMENTATION_ROUTE_BASELINE =
  '34/34/5/0/1/1'

/**
 * The conservative Target B implementation summary. `implementationStatus` is
 * SCAFFOLD_READY (the engineering layers are drafted); `executionStatus` is
 * DISABLED. Every authorization verdict is frozen NO-GO; P0 resolved stays 0;
 * the route baseline is frozen unchanged.
 */
export const TARGET_B_IMPLEMENTATION_SUMMARY: TargetBImplementationSummary = deepFreeze({
  targetName: 'Target B — Production Runtime / Real Plugin Ecosystem',
  implementationStatus: 'SCAFFOLD_READY',
  executionStatus: 'DISABLED',
  productionRuntime: 'NO-GO',
  arbitraryPluginLoading: 'NO-GO',
  remoteRegistry: 'NO-GO',
  marketplace: 'NO-GO',
  webuiExecution: 'NO-GO',
  approvalAuthorization: 'NO-GO',
  productionRollout: 'NO-GO',
  p0Total: 24,
  p0Resolved: 0,
  p0PartialEvidence: 19,
  p0PendingHumanReview: 5,
  pendingHumanReviewGates: ['P0-15', 'P0-16', 'P0-18', 'P0-19', 'P0-22'],
  requiredBeforeEnable: [
    'resolve P0 gates',
    'out-of-band human approval',
    'trust token',
    'production signature verifier',
    'sandbox worker lifecycle',
    'registry trust policy',
    'network allowlist',
    'secret handling',
    'rollback plan',
    'incident response',
    'route authorization',
  ],
})

/**
 * The Target B implementation layer board. Twelve drafted layers — every one
 * is disabled, non-executing, non-networking, non-production, and adds no route.
 * Each states its risk level and the human gate required before it could ever
 * be enabled. Frozen so a governance pass can never flip a capability.
 */
export const TARGET_B_IMPLEMENTATION_LAYERS: readonly TargetBImplementationLayer[] = deepFreeze([
  {
    key: 'common',
    layer: 'Shared Common Helpers',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    riskLevel: 'medium',
    requiredGate: 'n/a (pure helpers)',
  },
  {
    key: 'package',
    layer: 'Signed Plugin Package Schema',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    riskLevel: 'high',
    requiredGate: 'supply-chain policy (P0-05)',
  },
  {
    key: 'signature',
    layer: 'Plugin Signature Verification',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    riskLevel: 'critical',
    requiredGate: 'signature verification + trust policy',
  },
  {
    key: 'permissions',
    layer: 'Permission / Capability Model',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    riskLevel: 'high',
    requiredGate: 'permission model approval (P0-06)',
  },
  {
    key: 'registry',
    layer: 'Registry Trust Policy',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    riskLevel: 'critical',
    requiredGate: 'registry trust policy + network review',
  },
  {
    key: 'sandbox',
    layer: 'Sandbox Broker',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    riskLevel: 'critical',
    requiredGate: 'approved sandbox / worker lifecycle (P0-19)',
  },
  {
    key: 'approval',
    layer: 'Approval / Authorization Gate',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    riskLevel: 'critical',
    requiredGate: 'implementation authorization (P0-15 / P0-22)',
  },
  {
    key: 'executionPolicy',
    layer: 'Execution Policy Gate',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    riskLevel: 'critical',
    requiredGate: 'all gates + route authorization',
  },
  {
    key: 'runtime',
    layer: 'Runtime Orchestrator',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    riskLevel: 'critical',
    requiredGate: 'all gates + runtime authorization',
  },
  {
    key: 'audit',
    layer: 'Audit Trail',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    riskLevel: 'medium',
    requiredGate: 'audit / redaction model (P0-07)',
  },
  {
    key: 'rollback',
    layer: 'Rollback / Kill Switch',
    status: 'DESIGNED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    riskLevel: 'high',
    requiredGate: 'rollback / incident plan (P0-21 / P0-23)',
  },
  {
    key: 'report',
    layer: 'End-to-End Readiness Report',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    riskLevel: 'medium',
    requiredGate: 'n/a (aggregate projection)',
  },
])

/**
 * A frozen, fake, non-executable signed plugin package schema preview. Every
 * value is a documentation placeholder. No real plugin file is loaded, no
 * entrypoint is executed, no registry source is fetched, no checksum is
 * computed, and no signature is verified. The example registry source uses a
 * reserved `.invalid` domain that is never contacted.
 */
export const TARGET_B_PACKAGE_SCHEMA: TargetBPackageSchemaPreview = deepFreeze({
  packageId: 'example.plugin.alpha',
  packageName: 'Example Plugin Alpha (placeholder)',
  version: '0.1.0',
  publisher: 'example.publisher',
  manifestVersion: '1.0',
  hermesMinVersion: '0.0.0',
  descriptor: 'descriptor-only preview (no module path)',
  capabilities: ['display.surface', 'read.capability'],
  permissions: ['filesystem.read'],
  entrypoints: ['tool:example.tool.alpha'],
  checksum: 'sha256:' + '0000000000000000000000000000000000000000000000000000000000000000',
  signature: 'fixture-hmac-sha256:' + 'AA'.repeat(32),
  signatureAlgorithm: 'fixture-hmac-sha256',
  registrySource: 'https://registry.example.invalid',
  sandboxProfile: 'sandbox profile preview (no enforcement)',
  exampleOnly: true,
  notLoaded: true,
  notExecutable: true,
})

/**
 * The frozen implementation permission model entries (15 permissions). Every
 * permission is denied by default — none is granted, no matter what renders or
 * what untrusted metadata a request carries. Frozen so a governance pass can
 * never grant one.
 */
export const TARGET_B_PERMISSION_ENTRIES: readonly TargetBImplementationPermissionEntry[] = deepFreeze([
  { key: 'filesystem.read', label: 'Filesystem read', risk: 'high', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
  { key: 'filesystem.write', label: 'Filesystem write', risk: 'critical', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
  { key: 'network.http', label: 'Network HTTP', risk: 'critical', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
  { key: 'network.registry', label: 'Network registry', risk: 'critical', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
  { key: 'secrets.read', label: 'Secrets read', risk: 'critical', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
  { key: 'provider.read', label: 'Provider read', risk: 'medium', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
  { key: 'provider.write', label: 'Provider write', risk: 'critical', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
  { key: 'ui.render', label: 'UI render (display only)', risk: 'medium', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
  { key: 'tool.invoke', label: 'Tool invoke', risk: 'critical', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
  { key: 'database.read', label: 'Database read', risk: 'high', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
  { key: 'database.write', label: 'Database write', risk: 'critical', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
  { key: 'process.spawn', label: 'Process spawn', risk: 'critical', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
  { key: 'runtime.execute', label: 'Runtime execute', risk: 'critical', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
  { key: 'plugin.install', label: 'Plugin install', risk: 'critical', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
  { key: 'marketplace.fetch', label: 'Marketplace fetch', risk: 'critical', currentStatus: 'DENIED_BY_DEFAULT', grantable: false },
])

/** The frozen implementation permission model aggregate. */
export const TARGET_B_PERMISSION_MODEL: TargetBImplementationPermissionModel = deepFreeze({
  entries: TARGET_B_PERMISSION_ENTRIES,
  defaultDisposition: 'DENIED_BY_DEFAULT',
  anyGranted: false,
  dangerousPermissionsDenied: true,
})

/** The frozen capability declaration entries (non-executable metadata). */
export const TARGET_B_CAPABILITY_ENTRIES: readonly TargetBCapabilityEntry[] = deepFreeze([
  { key: 'display.surface', label: 'Display surface', executable: false },
  { key: 'display.toolbar', label: 'Display toolbar', executable: false },
  { key: 'display.status', label: 'Display status', executable: false },
  { key: 'read.descriptor', label: 'Read descriptor', executable: false },
  { key: 'read.capability', label: 'Read capability', executable: false },
  { key: 'event.emit.readonly', label: 'Emit read-only event', executable: false },
])

/** The frozen capability declaration model aggregate. */
export const TARGET_B_CAPABILITY_MODEL: TargetBCapabilityModel = deepFreeze({
  entries: TARGET_B_CAPABILITY_ENTRIES,
  anyExecutable: false,
})

/** The frozen signature verification layer projection. */
export const TARGET_B_SIGNATURE_VERIFICATION: TargetBSignatureVerificationProjection = deepFreeze({
  verifierInterfaceImplemented: true,
  productionVerifierAuthorized: false,
  fixtureVerifierOnly: true,
  trusted: false,
  productionApproved: false,
  unsignedRejected: true,
  forgedRejected: true,
  marketplaceRejected: true,
  unknownPublisherRejected: true,
  signatureRequired: true,
  productionAuthorization: 'NO-GO',
})

/** The frozen registry trust policy projection. */
export const TARGET_B_REGISTRY_TRUST: TargetBRegistryTrustProjection = deepFreeze({
  registryMode: 'DISABLED',
  networkEnabled: false,
  fetchEnabled: false,
  marketplaceEnabled: false,
  allowUnsigned: false,
  trustedPublishersCount: 0,
  signatureRequired: true,
  registryUrlExample: 'https://registry.example.invalid',
  productionAuthorization: 'NO-GO',
})

/** The frozen sandbox broker projection. */
export const TARGET_B_SANDBOX_BROKER: TargetBSandboxBrokerProjection = deepFreeze({
  brokerInterfaceImplemented: true,
  brokerEnabled: false,
  executionAllowed: false,
  processSpawnAllowed: false,
  networkAllowed: false,
  filesystemWriteAllowed: false,
  secretsAllowed: false,
  profileDesignOnly: true,
  productionAuthorization: 'NO-GO',
})

/** The frozen approval / authorization gate projection. */
export const TARGET_B_APPROVAL_GATE: TargetBApprovalGateProjection = deepFreeze({
  humanApprovalRequired: true,
  trustTokenProvisioned: false,
  humanApprovalValid: false,
  fakeApprovalAccepted: false,
  aiApprovalAccepted: false,
  metadataApprovalAccepted: false,
  productionAuthorization: 'NO-GO',
})

/** The frozen execution policy projection. */
export const TARGET_B_EXECUTION_POLICY: TargetBExecutionPolicyProjection = deepFreeze({
  allowed: false,
  canExecutePlugin: false,
  canLoadPluginPackage: false,
  canFetchRegistry: false,
  canRenderWebuiExecuteControl: false,
  webuiExecuteEnabled: false,
  runtimeRouteEnabled: false,
  productionRuntimeEnabled: false,
  productionAuthorization: 'NO-GO',
  p0ResolvedCount: 0,
  routeGovernanceBaseline: '34/34/5/0/1/1',
  reasons: [
    'p0_resolved_count_is_zero',
    'required_gates_unresolved:P0-15|P0-16|P0-18|P0-19|P0-22',
    'human_approval_missing',
    'trust_token_missing',
    'signature_not_verified',
    'registry_trust_policy_not_valid',
    'sandbox_broker_not_enabled',
    'route_governance_not_authorized',
    'rollback_plan_not_accepted',
    'production_safety_not_accepted',
    'kill_switch_not_ready',
  ],
})

/** The frozen audit / rollback projection. */
export const TARGET_B_AUDIT_ROLLBACK: TargetBAuditRollbackProjection = deepFreeze({
  auditPersistence: 'in_memory_only',
  auditPersisted: false,
  auditJsonlWritten: false,
  secretsRedacted: true,
  killSwitchReady: 'DESIGN_READY_ONLY',
  productionRollbackAuthorized: false,
  productionRollout: 'NO-GO',
  productionGatewayUntouched: true,
})

/**
 * The enablement blockers — what must be completed before Target B could even
 * be considered. Every blocker stays unresolved (resolved false). Frozen so a
 * governance pass can never silently resolve one.
 */
export const TARGET_B_IMPLEMENTATION_BLOCKERS: readonly TargetBImplementationBlocker[] = deepFreeze([
  { key: 'p0Gates', label: 'Resolve P0 gates', resolved: false, detail: '24 P0 gates, 0 resolved; P0-15 / P0-16 / P0-18 / P0-19 / P0-22 require out-of-band human review.' },
  { key: 'humanApproval', label: 'Out-of-band human approval', resolved: false, detail: 'A signed human approval (token-derived signature) is required; no trust token is provisioned.' },
  { key: 'trustToken', label: 'Trust token', resolved: false, detail: 'No out-of-band trust token is provisioned; metadata cannot mint one.' },
  { key: 'signatureVerifier', label: 'Production signature verifier', resolved: false, detail: 'The verifier interface is scaffolded; the production verifier is not authorized (fixture-only).' },
  { key: 'sandboxWorker', label: 'Sandbox worker lifecycle', resolved: false, detail: 'The broker interface is scaffolded; no approved production sandbox / worker lifecycle exists.' },
  { key: 'registryTrust', label: 'Registry trust policy', resolved: false, detail: 'The trust policy is scaffolded disabled; no reviewed, pinned, signed registry exists.' },
  { key: 'networkAllowlist', label: 'Network allowlist', resolved: false, detail: 'No external-network allowlist review; external network stays denied.' },
  { key: 'secretHandling', label: 'Secret handling', resolved: false, detail: 'No approved secret-handling policy; no real API key is read.' },
  { key: 'rollbackPlan', label: 'Rollback plan', resolved: false, detail: 'The kill switch is design-ready only; no approved rollback / incident plan exists.' },
  { key: 'routeAuthorization', label: 'Route authorization', resolved: false, detail: 'No route-governance authorization for any execution / install / approval / registry route.' },
])

/** Frozen page-header status badges (explicit non-color text). */
export const TARGET_B_IMPLEMENTATION_STATUS_BADGES: readonly TargetBImplementationStatusBadge[] = deepFreeze([
  { label: 'IMPLEMENTATION SCAFFOLD' },
  { label: 'EXECUTION DISABLED' },
  { label: 'PRODUCTION NO-GO' },
  { label: 'WEBUI EXECUTION DISABLED' },
  { label: 'REGISTRY DISABLED' },
  { label: 'MARKETPLACE DISABLED' },
  { label: 'APPROVAL NO-GO' },
  { label: 'P0 RESOLVED 0' },
])

/** Frozen boundary-banner rows (icon kind + explicit non-color text). */
export const TARGET_B_IMPLEMENTATION_BOUNDARY_ITEMS: readonly TargetBImplementationBoundaryItem[] = deepFreeze([
  { kind: 'lock', label: 'IMPLEMENTATION SCAFFOLD — full engineering path drafted, every layer disabled' },
  { kind: 'ban', label: 'NO production plugin runtime' },
  { kind: 'ban', label: 'NO arbitrary / signed plugin loading' },
  { kind: 'ban', label: 'NO local plugin directory loading' },
  { kind: 'ban', label: 'NO remote registry fetch / NO marketplace / NO external network' },
  { kind: 'ban', label: 'NO real API key read / NO real signature material / NO trust token' },
  { kind: 'ban', label: 'NO WebUI execution / NO execute button / NO submit control' },
  { kind: 'ban', label: 'NO approval / authorize / signoff / resolve control' },
  { kind: 'ban', label: 'NO production rollout / NO production rollback authorization' },
  { kind: 'ban', label: 'NO new backend route — route counts unchanged' },
])

/**
 * Global actions the WebUI must NOT offer on this surface. Rendered as
 * forbidden explanatory TEXT only — never as an interactive control.
 */
export const TARGET_B_IMPLEMENTATION_FORBIDDEN_ACTIONS: readonly string[] = deepFreeze([
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
  'load plugin',
  'upload plugin',
  'fetch plugin',
  'install plugin',
  'remote registry fetch',
  'marketplace',
  'external network',
  'real API key entry',
  'file upload',
  'JSON execution input',
  'trust token input',
  'signature upload',
  'run plugin from WebUI',
  'batch execute from WebUI',
])

/**
 * Global UI actions the read-only surface MAY offer. Every one is a harmless
 * client-only affordance that operates on static data — none calls the backend,
 * the runtime, the CLI, or the network.
 */
export const TARGET_B_IMPLEMENTATION_ALLOWED_UI_ACTIONS: readonly string[] = deepFreeze([
  'inspect implementation layer',
  'filter implementation layers',
  'copy implementation summary',
  'view Target A region',
  'view Target B readiness region',
  'view Runtime Governance section',
  'view Human Review section',
  'read NO-GO explanation',
])
