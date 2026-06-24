/**
 * Frozen static Target B Readiness manifest — Phase 4A (frontend mirror).
 *
 * A tracked, reviewable, deterministic mirror of the **Target B readiness
 * scaffold** state. Target B is the long-term goal of opening a real production
 * plugin runtime (signed / arbitrary plugin loading, a remote registry, a
 * marketplace, WebUI execution, and a production rollout). Phase 4A implements
 * ONLY the readiness scaffold — the architecture models, the disabled
 * interfaces, the permission / approval gate models, the read-only WebUI
 * preview, and the tests proving every dangerous capability is still disabled.
 *
 * This manifest carries ONLY safe, value-free, disabled fields — no API key,
 * Authorization, Bearer, secret, callable repr, shell command, SQL statement,
 * production path, local plugin path, dynamic import path, executable
 * entrypoint, real external URL, download URL, install command, real registry
 * token, real plugin signature, or production home path.
 *
 * Provenance: derived from the frozen backend disabled scaffold in
 *   - hermes_cli/dev_web_target_b_readiness.py (architecture, permission model,
 *     registry protocol, approval gate, deny builders, disabled report)
 *   - hermes_cli/dev_web_p0_evidence.py        (P0 gates, frozen NO-GO flags)
 *   - hermes_cli/dev_web_safety_baseline.py    (route-governance 34/34/5/0/1/1)
 *
 * The WebUI does NOT call the CLI, does NOT run the Python runtime, does NOT
 * spawn a process, does NOT fetch a remote registry, does NOT open a
 * marketplace, does NOT load a plugin, does NOT read or write files, and does
 * NOT access production or the production home. Every value here is static and
 * deterministic — no current time, no random id, no uuid, no network fetch.
 *
 * This manifest describes the readiness scaffold ONLY — it never grants
 * permission, never loads a plugin, never executes a plugin, never fetches a
 * registry, never opens a marketplace, never reads a real API key, never
 * provisions a trust token, never approves a gate, never authorizes a runtime,
 * and never resolves a P0 gate. Execution stays DISABLED, every authorization
 * verdict stays NO-GO, every permission stays DENIED_BY_DEFAULT, and P0
 * resolved stays 0 no matter what renders.
 */

import type {
  TargetBReadinessSummary,
  TargetBArchitectureModule,
  PluginPackageSchemaPreview,
  TargetBPermissionEntry,
  RegistryProtocolPreview,
  WebUIExecutionPreview,
  ApprovalGateModel,
  TargetBEnablementBlocker,
  TargetBTargetARelationship,
  TargetBReadinessCheckItem,
  TargetBStatusBadge,
  TargetBBoundaryItem,
  TARGET_B_ROUTE_BASELINE,
} from '@/types/api/targetBReadiness'

/**
 * Recursively deep-freeze a value (arrays + nested objects). Applied to every
 * exported constant so the canonical readiness state is immutable at runtime —
 * an external caller can never mutate a returned projection into the canonical
 * manifest, never flip a frozen NO-GO verdict, never flip a frozen disabled
 * capability, never flip a frozen DENIED_BY_DEFAULT permission, never flip a
 * frozen false execution flag, and never raise P0 resolved above 0. Reads,
 * spreads, and `.map()` copies are unaffected. Pure and total.
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

/** Schema version (mirrors TARGET_B_READINESS_SCHEMA_VERSION). */
export const TARGET_B_READINESS_VERSION = deepFreeze('phase-4a-target-b-readiness-v1')

/** Frozen phase label for the Target B readiness region. */
export const TARGET_B_READINESS_PHASE_LABEL = deepFreeze('Phase 4A')

/** Frozen route-governance baseline (unchanged by this read-only surface). */
export const TARGET_B_ROUTE_GOVERNANCE_BASELINE: typeof TARGET_B_ROUTE_BASELINE = '34/34/5/0/1/1'

/**
 * The conservative Target B readiness summary. `readinessStatus` is
 * SCAFFOLD_READY (the architecture models and disabled interfaces are drafted);
 * `executionStatus` is DISABLED. Every authorization verdict is frozen NO-GO;
 * P0 resolved stays 0; the route baseline is frozen unchanged.
 */
export const TARGET_B_READINESS_SUMMARY: TargetBReadinessSummary = deepFreeze({
  targetName: 'Target B — Production Runtime / Real Plugin Ecosystem',
  readinessStatus: 'SCAFFOLD_READY',
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
  p0PendingHumanReview: 5,
  requiredBeforeEnable: [
    'trusted human approval',
    'signature verification implementation',
    'sandbox enforcement',
    'registry trust policy',
    'network policy',
    'secret handling policy',
    'rollback plan',
    'production incident response',
    'route governance authorization',
  ],
})

/**
 * The Target B architecture module board. Sixteen designed modules — every one
 * is disabled, non-executing, non-networking, non-production, and adds no route.
 * Each states its risk level and the human gate required before it could ever
 * be implemented. Frozen so a governance pass can never flip a capability to
 * enabled / executing / networking / production.
 */
export const TARGET_B_ARCHITECTURE_MODULES: readonly TargetBArchitectureModule[] = deepFreeze([
  {
    key: 'packageFormat',
    module: 'Plugin Package Format',
    status: 'DESIGNED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'high',
    requiredGate: 'supply-chain policy review (P0-05)',
    futureImplementationNotes:
      'A signed, versioned package format is designed only. No package is loaded or unpacked.',
  },
  {
    key: 'pluginSignatureVerification',
    module: 'Plugin Signature Verification',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'critical',
    requiredGate: 'signature verification implementation',
    futureImplementationNotes:
      'A signature requirement is scaffolded but no verifier exists; unsigned plugins are never accepted.',
  },
  {
    key: 'pluginPermissionModel',
    module: 'Plugin Permission Model',
    status: 'DESIGNED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'high',
    requiredGate: 'permission model approval (P0-06)',
    futureImplementationNotes:
      'A deny-by-default permission taxonomy is designed; every permission stays denied by default.',
  },
  {
    key: 'pluginCapabilityDeclaration',
    module: 'Plugin Capability Declaration',
    status: 'DESIGNED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'medium',
    requiredGate: 'capability review board',
    futureImplementationNotes:
      'Capability declarations are designed as metadata only; they grant nothing at runtime.',
  },
  {
    key: 'remoteRegistryProtocol',
    module: 'Remote Registry Protocol',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'critical',
    requiredGate: 'registry trust policy + external-network review',
    futureImplementationNotes:
      'A pinned, signed registry protocol is scaffolded; no registry is ever fetched and no network is opened.',
  },
  {
    key: 'registryTrustPolicy',
    module: 'Registry Trust Policy',
    status: 'DESIGNED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'critical',
    requiredGate: 'registry trust policy approval',
    futureImplementationNotes:
      'A trust policy is designed; no trust decision is granted to any source.',
  },
  {
    key: 'marketplacePolicy',
    module: 'Marketplace Policy',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'critical',
    requiredGate: 'marketplace trust model + human approval',
    futureImplementationNotes:
      'A marketplace policy is scaffolded; no marketplace is reachable and no listing is fetched.',
  },
  {
    key: 'runtimeSandboxBoundary',
    module: 'Runtime Sandbox Boundary',
    status: 'DESIGNED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'critical',
    requiredGate: 'approved sandbox model (P0-01 / P0-19)',
    futureImplementationNotes:
      'A sandbox boundary is designed; the dev skeleton is not an approved production sandbox.',
  },
  {
    key: 'executionBroker',
    module: 'Execution Broker',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'critical',
    requiredGate: 'worker lifecycle approval (P0-19)',
    futureImplementationNotes:
      'An execution broker is scaffolded as disabled; no plugin is executed and no worker lifecycle exists.',
  },
  {
    key: 'webuiExecutionRequestFlow',
    module: 'WebUI Execution Request Flow',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'high',
    requiredGate: 'execution-route review + human approval',
    futureImplementationNotes:
      'A request flow is previewed read-only; there is no execution route and no submit control.',
  },
  {
    key: 'approvalAuthorizationGate',
    module: 'Approval / Authorization Gate',
    status: 'DESIGNED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'critical',
    requiredGate: 'implementation authorization (P0-15 / P0-22)',
    futureImplementationNotes:
      'A human approval gate is designed; no trust token is provisioned and metadata cannot approve.',
  },
  {
    key: 'auditTrail',
    module: 'Audit Trail',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'medium',
    requiredGate: 'audit / redaction model approval (P0-07)',
    futureImplementationNotes:
      'An audit trail is scaffolded in-memory only; no persistent runtime audit store is committed.',
  },
  {
    key: 'rollbackKillSwitch',
    module: 'Rollback / Kill Switch',
    status: 'DESIGNED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'high',
    requiredGate: 'rollback / incident plan approval (P0-21 / P0-23)',
    futureImplementationNotes:
      'A rollback / kill-switch model is designed; no approved rollback or incident plan exists.',
  },
  {
    key: 'secretHandlingBoundary',
    module: 'Secret Handling Boundary',
    status: 'DESIGNED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'critical',
    requiredGate: 'secret handling policy (P0-10)',
    futureImplementationNotes:
      'A secret handling boundary is designed; no real API key is read and secrets are redacted.',
  },
  {
    key: 'networkPolicy',
    module: 'Network Policy',
    status: 'SCAFFOLDED_DISABLED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'critical',
    requiredGate: 'external-network allowlist + human approval',
    futureImplementationNotes:
      'A network policy is scaffolded; external network stays denied and no outbound path exists.',
  },
  {
    key: 'productionRolloutPlan',
    module: 'Production Rollout Plan',
    status: 'DESIGNED',
    enabled: false,
    executionCapable: false,
    networkCapable: false,
    productionCapable: false,
    routeImpact: 'none',
    riskLevel: 'critical',
    requiredGate: 'production rollout authorization (P0-15)',
    futureImplementationNotes:
      'A rollout plan is designed only; production rollout stays NO-GO and no trust token is provisioned.',
  },
])

/**
 * A fake, static, non-executable plugin package schema preview. Every value is
 * a documentation placeholder. No real plugin file is loaded, no entrypoint is
 * executed, no registry source is fetched, no checksum is verified, and no
 * signature material is carried. The example registry source uses a reserved
 * `.invalid` domain that is never contacted.
 */
export const TARGET_B_PLUGIN_PACKAGE_SCHEMA: PluginPackageSchemaPreview = deepFreeze({
  packageId: 'example.plugin.alpha (placeholder)',
  version: '0.0.0-placeholder',
  descriptor: 'descriptor-only preview (no module path)',
  capabilities: ['example.capability.read (placeholder)'],
  permissions: ['example.permission.read (placeholder)'],
  entrypoints: ['entrypoint preview (not executed)'],
  signature: 'signature_required_not_provided',
  publisher: 'example publisher (placeholder)',
  registrySource: 'https://registry.example.invalid',
  checksum: 'checksum_required_not_provided',
  sandboxProfile: 'sandbox profile preview (no enforcement)',
  minimumHermesVersion: '0.0.0-placeholder',
  exampleOnly: true,
  notLoaded: true,
  notExecutable: true,
})

/**
 * The frozen plugin permission model entries. Every permission is denied by
 * default — none is granted, no matter what renders or what untrusted metadata
 * a request carries. Frozen so a governance pass can never grant one.
 */
export const TARGET_B_PERMISSION_ENTRIES: readonly TargetBPermissionEntry[] = deepFreeze([
  { key: 'filesystem.read', label: 'Filesystem read', currentStatus: 'DENIED_BY_DEFAULT' },
  { key: 'filesystem.write', label: 'Filesystem write', currentStatus: 'DENIED_BY_DEFAULT' },
  { key: 'network.http', label: 'Network HTTP', currentStatus: 'DENIED_BY_DEFAULT' },
  { key: 'network.registry', label: 'Network registry', currentStatus: 'DENIED_BY_DEFAULT' },
  { key: 'secrets.read', label: 'Secrets read', currentStatus: 'DENIED_BY_DEFAULT' },
  { key: 'provider.read', label: 'Provider read', currentStatus: 'DENIED_BY_DEFAULT' },
  { key: 'provider.write', label: 'Provider write', currentStatus: 'DENIED_BY_DEFAULT' },
  { key: 'ui.render', label: 'UI render', currentStatus: 'DENIED_BY_DEFAULT' },
  { key: 'tool.invoke', label: 'Tool invoke', currentStatus: 'DENIED_BY_DEFAULT' },
  { key: 'database.read', label: 'Database read', currentStatus: 'DENIED_BY_DEFAULT' },
  { key: 'database.write', label: 'Database write', currentStatus: 'DENIED_BY_DEFAULT' },
  { key: 'process.spawn', label: 'Process spawn', currentStatus: 'DENIED_BY_DEFAULT' },
])

/**
 * The frozen remote registry protocol preview. The registry URL is a
 * documentation string using a reserved `.invalid` domain — it is NEVER
 * fetched. Network and fetch stay disabled; a signature is required; unsigned
 * packages are never allowed; the marketplace stays disabled.
 */
export const TARGET_B_REGISTRY_PROTOCOL: RegistryProtocolPreview = deepFreeze({
  registryUrlExample: 'https://registry.example.invalid',
  fetchEnabled: false,
  networkEnabled: false,
  trustPolicyRequired: true,
  signatureRequired: true,
  allowUnsigned: false,
  marketplaceEnabled: false,
})

/**
 * The frozen WebUI execution preview. The flow is visible in the WebUI but
 * every step is disabled, the execute button is disabled, the runtime route is
 * unavailable, and submission is impossible. Frozen so a governance pass can
 * never flip a step or the canSubmit flag.
 */
export const TARGET_B_WEBUI_EXECUTION: WebUIExecutionPreview = deepFreeze({
  visibleInWebUI: true,
  executeButtonEnabled: false,
  approvalRequired: true,
  runtimeRouteAvailable: false,
  canSubmit: false,
  status: 'PREVIEW_ONLY_DISABLED',
  flow: [
    {
      key: 'selectPackage',
      label: 'Select plugin package',
      enabled: false,
      note: 'disabled preview only',
    },
    {
      key: 'validateSignature',
      label: 'Validate signature',
      enabled: false,
      note: 'not implemented / required',
    },
    {
      key: 'requestApproval',
      label: 'Request approval',
      enabled: false,
      note: 'disabled',
    },
    {
      key: 'execute',
      label: 'Execute',
      enabled: false,
      note: 'disabled',
    },
    {
      key: 'audit',
      label: 'Audit',
      enabled: false,
      note: 'preview only',
    },
  ],
})

/**
 * The frozen approval / authorization gate model. Human approval is required;
 * no trust token is provisioned; fake, AI-attributed, and metadata approvals
 * are all rejected. Production authorization stays NO-GO. Frozen so a
 * governance pass can never provision a token or accept a fake approval.
 */
export const TARGET_B_APPROVAL_GATE: ApprovalGateModel = deepFreeze({
  humanApprovalRequired: true,
  trustTokenProvisioned: false,
  fakeApprovalAccepted: false,
  aiApprovalAccepted: false,
  metadataApprovalAccepted: false,
  productionAuthorization: 'NO-GO',
})

/**
 * The enablement blockers — what must be completed before Target B could even
 * be considered. Every blocker stays unresolved (resolved false). Frozen so a
 * governance pass can never silently resolve one.
 */
export const TARGET_B_ENABLEMENT_BLOCKERS: readonly TargetBEnablementBlocker[] = deepFreeze([
  {
    key: 'humanApproval',
    label: 'Trusted human approval',
    resolved: false,
    detail: 'The five pending P0 gates (P0-15 / P0-16 / P0-18 / P0-19 / P0-22) require an out-of-band human approval.',
  },
  {
    key: 'signatureVerifier',
    label: 'Signature verifier',
    resolved: false,
    detail: 'No plugin signature verifier is implemented; unsigned plugins are never accepted.',
  },
  {
    key: 'sandboxEnforcement',
    label: 'Sandbox enforcement',
    resolved: false,
    detail: 'No approved production sandbox / worker lifecycle model exists.',
  },
  {
    key: 'registryTrustPolicy',
    label: 'Registry trust policy',
    resolved: false,
    detail: 'No reviewed registry trust policy or pinned, signed registry exists.',
  },
  {
    key: 'networkAllowlist',
    label: 'Network allowlist',
    resolved: false,
    detail: 'No external-network allowlist review; external network stays denied.',
  },
  {
    key: 'secretHandling',
    label: 'Secret handling',
    resolved: false,
    detail: 'No approved secret-handling policy; no real API key is read.',
  },
  {
    key: 'routeAuthorization',
    label: 'Route authorization',
    resolved: false,
    detail: 'No route-governance authorization for any execution / install / approval / registry route.',
  },
  {
    key: 'rollback',
    label: 'Rollback plan',
    resolved: false,
    detail: 'No approved rollback / incident-response plan.',
  },
  {
    key: 'incidentResponse',
    label: 'Incident response',
    resolved: false,
    detail: 'No approved production incident-response plan or trust token.',
  },
])

/**
 * The Target A relationship — how the completed dev-only prototype (Target A)
 * relates to Target B. Target A complete is prerequisite *evidence* only; it
 * does NOT authorize Target B; Target B remains disabled until the gates
 * resolve. Frozen so a governance pass can never imply Target A authorizes
 * Target B.
 */
export const TARGET_B_TARGET_A_RELATIONSHIP: readonly TargetBTargetARelationship[] = deepFreeze([
  {
    key: 'prerequisiteEvidence',
    statement: 'Target A complete is prerequisite evidence for any future Target B review.',
  },
  {
    key: 'doesNotAuthorize',
    statement: 'Target A complete does NOT authorize Target B.',
  },
  {
    key: 'remainsDisabled',
    statement: 'Target B remains disabled until the human-approval gates are resolved.',
  },
])

/**
 * The Target B readiness checklist. Design-drafting items are 'ready' (the
 * scaffold is drafted); enablement items are 'blocked' (production capabilities
 * stay disabled). None of the blocked items says the system is production-ready.
 * Frozen so a governance pass can never flip a blocked item to ready.
 */
export const TARGET_B_READINESS_CHECKLIST: readonly TargetBReadinessCheckItem[] = deepFreeze([
  { id: 'packageSchemaDrafted', label: 'Plugin package schema drafted', status: 'ready', enablementBlocked: false, evidenceSummary: 'A signed, versioned package format is designed as a static schema preview.' },
  { id: 'signatureModelDrafted', label: 'Signature model drafted', status: 'ready', enablementBlocked: false, evidenceSummary: 'A signature requirement is scaffolded; no verifier is implemented.' },
  { id: 'permissionModelDrafted', label: 'Permission model drafted', status: 'ready', enablementBlocked: false, evidenceSummary: 'A deny-by-default permission taxonomy is designed.' },
  { id: 'registryProtocolDrafted', label: 'Registry protocol drafted', status: 'ready', enablementBlocked: false, evidenceSummary: 'A pinned, signed registry protocol is scaffolded as a disabled preview.' },
  { id: 'sandboxBoundaryDrafted', label: 'Sandbox boundary drafted', status: 'ready', enablementBlocked: false, evidenceSummary: 'A sandbox boundary is designed; not an approved production sandbox.' },
  { id: 'approvalGatesDrafted', label: 'Approval gates drafted', status: 'ready', enablementBlocked: false, evidenceSummary: 'A human approval gate is designed; no trust token is provisioned.' },
  { id: 'webuiPreviewDrafted', label: 'WebUI preview drafted', status: 'ready', enablementBlocked: false, evidenceSummary: 'A read-only WebUI preview is rendered; no execution control exists.' },
  { id: 'auditRollbackDrafted', label: 'Audit / rollback plan drafted', status: 'ready', enablementBlocked: false, evidenceSummary: 'An audit trail and rollback model are scaffolded; no approved plan exists.' },
  { id: 'executionDisabled', label: 'Execution disabled', status: 'ready', enablementBlocked: false, evidenceSummary: 'Execution stays DISABLED; no plugin is executed.' },
  { id: 'networkDisabled', label: 'Network disabled', status: 'ready', enablementBlocked: false, evidenceSummary: 'Network stays disabled; no outbound path exists.' },
  { id: 'productionDisabled', label: 'Production disabled', status: 'ready', enablementBlocked: false, evidenceSummary: 'Production stays disabled; no production access of any kind.' },
  { id: 'routeUnchanged', label: 'Route unchanged', status: 'ready', enablementBlocked: false, evidenceSummary: 'Route governance unchanged (34/34/5/0/1/1); no route added.' },
  { id: 'p0UnresolvedVisible', label: 'P0 unresolved visible', status: 'ready', enablementBlocked: false, evidenceSummary: 'P0 resolved stays 0; five gates remain pending human review.' },
  { id: 'productionRuntimeEnablement', label: 'Production runtime enablement', status: 'blocked', enablementBlocked: true, evidenceSummary: 'Production runtime remains NO-GO; approved sandbox / worker lifecycle required.' },
  { id: 'registryEnablement', label: 'Registry enablement', status: 'blocked', enablementBlocked: true, evidenceSummary: 'Remote registry remains disabled; registry trust policy required.' },
  { id: 'marketplaceEnablement', label: 'Marketplace enablement', status: 'blocked', enablementBlocked: true, evidenceSummary: 'Marketplace remains disabled; reviewed marketplace trust model required.' },
])

/** Frozen page-header status badges (explicit non-color text). */
export const TARGET_B_STATUS_BADGES: readonly TargetBStatusBadge[] = deepFreeze([
  { label: 'READINESS SCAFFOLD' },
  { label: 'EXECUTION DISABLED' },
  { label: 'PRODUCTION NO-GO' },
  { label: 'REGISTRY DISABLED' },
  { label: 'MARKETPLACE DISABLED' },
  { label: 'APPROVAL REQUIRED' },
])

/** Frozen boundary-banner rows (icon kind + explicit non-color text). */
export const TARGET_B_BOUNDARY_ITEMS: readonly TargetBBoundaryItem[] = deepFreeze([
  { kind: 'lock', label: 'READINESS SCAFFOLD — architecture models and disabled interfaces only' },
  { kind: 'ban', label: 'NO production plugin runtime' },
  { kind: 'ban', label: 'NO arbitrary / signed plugin loading' },
  { kind: 'ban', label: 'NO local plugin directory loading' },
  { kind: 'ban', label: 'NO remote registry fetch / NO marketplace / NO external network' },
  { kind: 'ban', label: 'NO real API key read / NO real signature material' },
  { kind: 'ban', label: 'NO WebUI execution / NO execute button / NO submit control' },
  { kind: 'ban', label: 'NO approval / authorize / signoff / resolve control' },
  { kind: 'ban', label: 'NO production rollout / NO trust token provisioned' },
  { kind: 'ban', label: 'NO new backend route — route counts unchanged' },
])

/**
 * Global actions the WebUI must NOT offer on this surface. Rendered as
 * forbidden explanatory TEXT only — never as an interactive control.
 */
export const TARGET_B_FORBIDDEN_ACTIONS: readonly string[] = deepFreeze([
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
export const TARGET_B_ALLOWED_UI_ACTIONS: readonly string[] = deepFreeze([
  'inspect architecture module',
  'filter architecture modules',
  'copy readiness summary',
  'view Target A region',
  'view Runtime Governance section',
  'view Human Review section',
  'read NO-GO explanation',
])
