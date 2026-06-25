/**
 * Target B Implementation pure view-model projections (Phase 4B).
 *
 * Pure, deterministic, side-effect-free functions that turn the frozen static
 * manifest (@/constants/targetBImplementationManifest) into the read-only shapes
 * the Target B Implementation region renders. No current time, no random id,
 * no uuid, no network fetch, no file read, no file write, no process spawn,
 * no CLI call, no backend call.
 *
 * Every projection is value-free and defense-in-depth redacted: a conservative
 * sanitizer masks any secret-shaped / production-path-shaped /
 * fake-approval-shaped / Target-B-authorization marker substring so a future
 * editor adding a secret or a fake authorization to the manifest can never leak
 * it through this surface. The manifest itself carries no secrets and no fake
 * authorizations today.
 *
 * Mutating any returned value can never reach the frozen canonical manifest,
 * can never flip a frozen NO-GO verdict, can never flip a frozen disabled
 * capability, can never grant a DENIED_BY_DEFAULT permission, can never enable
 * a disabled execution flag, and can never raise P0 resolved above 0.
 */

import {
  TARGET_B_IMPLEMENTATION_VERSION,
  TARGET_B_IMPLEMENTATION_PHASE_LABEL,
  TARGET_B_IMPLEMENTATION_ROUTE_GOVERNANCE_BASELINE,
  TARGET_B_IMPLEMENTATION_SUMMARY,
  TARGET_B_IMPLEMENTATION_LAYERS,
  TARGET_B_PACKAGE_SCHEMA,
  TARGET_B_PERMISSION_ENTRIES,
  TARGET_B_CAPABILITY_ENTRIES,
  TARGET_B_SIGNATURE_VERIFICATION,
  TARGET_B_REGISTRY_TRUST,
  TARGET_B_SANDBOX_BROKER,
  TARGET_B_APPROVAL_GATE,
  TARGET_B_EXECUTION_POLICY,
  TARGET_B_AUDIT_ROLLBACK,
  TARGET_B_IMPLEMENTATION_BLOCKERS,
  TARGET_B_IMPLEMENTATION_STATUS_BADGES,
  TARGET_B_IMPLEMENTATION_BOUNDARY_ITEMS,
  TARGET_B_IMPLEMENTATION_FORBIDDEN_ACTIONS,
  TARGET_B_IMPLEMENTATION_ALLOWED_UI_ACTIONS,
} from '@/constants/targetBImplementationManifest'
import type {
  TargetBImplementationViewModel,
  TargetBImplementationSummary,
  TargetBImplementationLayer,
  TargetBPackageSchemaPreview,
  TargetBImplementationPermissionModel,
  TargetBImplementationPermissionEntry,
  TargetBCapabilityModel,
  TargetBCapabilityEntry,
  TargetBSignatureVerificationProjection,
  TargetBRegistryTrustProjection,
  TargetBSandboxBrokerProjection,
  TargetBApprovalGateProjection,
  TargetBExecutionPolicyProjection,
  TargetBAuditRollbackProjection,
  TargetBImplementationBlocker,
  TargetBImplementationStatusBadge,
  TargetBImplementationBoundaryItem,
  TargetBImplementationSummaryCard,
  TargetBLayerFilterKey,
} from '@/types/api/targetBImplementation'

/**
 * Secret / production-path / fake-authorization stems a defense-in-depth
 * redactor masks. These are *patterns* (not real values) — they exist only to
 * scrub a substring should one ever reach this surface. Comparison is
 * case-insensitive, so stems are written in their canonical lower-case form.
 */
const REDACT_STEMS: readonly string[] = [
  'sk-',
  'bearer ',
  'authorization:',
  'ghp_',
  'xox',
  'begin private key',
  '~/.hermes',
  '.hermes/',
  'state.db',
  'implementation_authorization=go',
  'implementation authorization = go',
  'openai_api_key',
  'db_password',
  'accesstoken',
  'phase_3i_authorized=true',
  'production_approved=true',
  'route_exception_approved=true',
  'approved_by_ai=true',
  'trust_token=fake',
  'trust_token=',
  'target_b_authorized=true',
  'target_b_authorized=',
  'production_runtime_go=true',
  'production_runtime_go=',
  'registry_token=fake',
  'registry_token=',
  'plugin_signature=fake-private-key',
  'plugin_signature=',
]

/** Mask placeholder emitted by the defense-in-depth redactor. */
const REDACTED = '[REDACTED]'

/**
 * Defense-in-depth redactor. Masks any secret-shaped / production-path-shaped /
 * fake-authorization-shaped substring in *value*. Pure and total — never
 * throws, never reads files or the network. Applied only to free-text fields
 * projected for display.
 */
export function redactTargetBImplementationValue(value: string): string {
  if (typeof value !== 'string' || value.length === 0) return ''
  for (const stem of REDACT_STEMS) {
    if (value.toLowerCase().includes(stem.toLowerCase())) {
      return REDACTED
    }
  }
  return value
}

/** Stable public alias for {@link redactTargetBImplementationValue}. */
export function sanitizeTargetBImplementationDisplayText(value: string): string {
  return redactTargetBImplementationValue(value)
}

/** True iff every authorization verdict in the summary is frozen NO-GO. */
export function allTargetBImplementationVerdictsNoGo(
  summary: TargetBImplementationSummary,
): boolean {
  return (
    summary.productionRuntime === 'NO-GO' &&
    summary.arbitraryPluginLoading === 'NO-GO' &&
    summary.remoteRegistry === 'NO-GO' &&
    summary.marketplace === 'NO-GO' &&
    summary.webuiExecution === 'NO-GO' &&
    summary.approvalAuthorization === 'NO-GO' &&
    summary.productionRollout === 'NO-GO'
  )
}

/** True iff every implementation layer is disabled / non-executing / non-networking. */
export function allTargetBImplementationLayersDisabled(
  layers: readonly TargetBImplementationLayer[],
): boolean {
  return (
    layers.length > 0 &&
    layers.every(
      (l) =>
        l.enabled === false &&
        l.executionCapable === false &&
        l.networkCapable === false &&
        l.productionCapable === false,
    )
  )
}

/** True iff every permission is denied by default. */
export function allTargetBImplementationPermissionsDenied(
  entries: readonly TargetBImplementationPermissionEntry[],
): boolean {
  return (
    entries.length > 0 && entries.every((p) => p.currentStatus === 'DENIED_BY_DEFAULT')
  )
}

/** Project the frozen summary (defensive copy + redacted free-text). Deterministic. */
export function buildTargetBImplementationSummary(): TargetBImplementationSummary {
  const s = TARGET_B_IMPLEMENTATION_SUMMARY
  return {
    ...s,
    targetName: redactTargetBImplementationValue(s.targetName),
    requiredBeforeEnable: s.requiredBeforeEnable.map((r) => redactTargetBImplementationValue(r)),
  }
}

/**
 * Project the implementation layer board (free-text fields defense-in-depth
 * redacted). Every nested collection is a fresh defensive copy, so mutating a
 * returned layer can never reach the frozen canonical manifest.
 */
export function buildTargetBImplementationLayers(): readonly TargetBImplementationLayer[] {
  return TARGET_B_IMPLEMENTATION_LAYERS.map((l) => ({
    ...l,
    layer: redactTargetBImplementationValue(l.layer),
    requiredGate: redactTargetBImplementationValue(l.requiredGate),
  }))
}

/** Project the signed package schema preview (free-text fields redacted). */
export function buildTargetBPackageSchema(): TargetBPackageSchemaPreview {
  const s = TARGET_B_PACKAGE_SCHEMA
  return {
    packageId: redactTargetBImplementationValue(s.packageId),
    packageName: redactTargetBImplementationValue(s.packageName),
    version: redactTargetBImplementationValue(s.version),
    publisher: redactTargetBImplementationValue(s.publisher),
    manifestVersion: redactTargetBImplementationValue(s.manifestVersion),
    hermesMinVersion: redactTargetBImplementationValue(s.hermesMinVersion),
    descriptor: redactTargetBImplementationValue(s.descriptor),
    capabilities: s.capabilities.map((c) => redactTargetBImplementationValue(c)),
    permissions: s.permissions.map((p) => redactTargetBImplementationValue(p)),
    entrypoints: s.entrypoints.map((e) => redactTargetBImplementationValue(e)),
    checksum: redactTargetBImplementationValue(s.checksum),
    signature: redactTargetBImplementationValue(s.signature),
    signatureAlgorithm: redactTargetBImplementationValue(s.signatureAlgorithm),
    registrySource: redactTargetBImplementationValue(s.registrySource),
    sandboxProfile: redactTargetBImplementationValue(s.sandboxProfile),
    exampleOnly: true,
    notLoaded: true,
    notExecutable: true,
  }
}

/** Project the frozen permission model (free-text redacted). Defensive copy. */
export function buildTargetBImplementationPermissionModel(): TargetBImplementationPermissionModel {
  const entries: readonly TargetBImplementationPermissionEntry[] = TARGET_B_PERMISSION_ENTRIES.map(
    (p) => ({
      key: p.key,
      label: redactTargetBImplementationValue(p.label),
      risk: p.risk,
      currentStatus: p.currentStatus,
      grantable: false,
    }),
  )
  return {
    entries,
    defaultDisposition: 'DENIED_BY_DEFAULT',
    anyGranted: false,
    dangerousPermissionsDenied: true,
  }
}

/** Project the frozen capability model (free-text redacted). Defensive copy. */
export function buildTargetBCapabilityModel(): TargetBCapabilityModel {
  const entries: readonly TargetBCapabilityEntry[] = TARGET_B_CAPABILITY_ENTRIES.map((c) => ({
    key: c.key,
    label: redactTargetBImplementationValue(c.label),
    executable: false,
  }))
  return {
    entries,
    anyExecutable: false,
  }
}

/** Project the frozen signature verification projection (defensive copy). */
export function buildTargetBSignatureVerification(): TargetBSignatureVerificationProjection {
  return { ...TARGET_B_SIGNATURE_VERIFICATION }
}

/** Project the frozen registry trust projection (defensive copy). */
export function buildTargetBRegistryTrust(): TargetBRegistryTrustProjection {
  return { ...TARGET_B_REGISTRY_TRUST }
}

/** Project the frozen sandbox broker projection (defensive copy). */
export function buildTargetBSandboxBroker(): TargetBSandboxBrokerProjection {
  return { ...TARGET_B_SANDBOX_BROKER }
}

/** Project the frozen approval gate projection (defensive copy). */
export function buildTargetBApprovalGate(): TargetBApprovalGateProjection {
  return { ...TARGET_B_APPROVAL_GATE }
}

/** Project the frozen execution policy projection (defensive copy). */
export function buildTargetBExecutionPolicy(): TargetBExecutionPolicyProjection {
  return {
    ...TARGET_B_EXECUTION_POLICY,
    reasons: [...TARGET_B_EXECUTION_POLICY.reasons],
  }
}

/** Project the frozen audit / rollback projection (defensive copy). */
export function buildTargetBAuditRollback(): TargetBAuditRollbackProjection {
  return { ...TARGET_B_AUDIT_ROLLBACK }
}

/** Project the enablement blockers (free-text redacted). Defensive copy. */
export function buildTargetBImplementationBlockers(): readonly TargetBImplementationBlocker[] {
  return TARGET_B_IMPLEMENTATION_BLOCKERS.map((b) => ({
    key: b.key,
    label: redactTargetBImplementationValue(b.label),
    resolved: false,
    detail: redactTargetBImplementationValue(b.detail),
  }))
}

/** Project the frozen status badges (defensive copy). Deterministic. */
export function buildTargetBImplementationStatusBadges(): readonly TargetBImplementationStatusBadge[] {
  return TARGET_B_IMPLEMENTATION_STATUS_BADGES.map((b) => ({
    label: redactTargetBImplementationValue(b.label),
  }))
}

/** Project the frozen boundary-banner rows (free-text redacted). Defensive copy. */
export function buildTargetBImplementationBoundaryItems(): readonly TargetBImplementationBoundaryItem[] {
  return TARGET_B_IMPLEMENTATION_BOUNDARY_ITEMS.map((row) => ({
    kind: row.kind,
    label: redactTargetBImplementationValue(row.label),
  }))
}

/** Project the forbidden-actions list (defensive copy). */
export function buildTargetBImplementationForbiddenActions(): readonly string[] {
  return [...TARGET_B_IMPLEMENTATION_FORBIDDEN_ACTIONS]
}

/** Project the allowed-UI-actions list (defensive copy). */
export function buildTargetBImplementationAllowedUiActions(): readonly string[] {
  return [...TARGET_B_IMPLEMENTATION_ALLOWED_UI_ACTIONS]
}

/** Summary cards for the implementation overview. Deterministic. */
export function buildTargetBImplementationSummaryCards(): readonly TargetBImplementationSummaryCard[] {
  const s = TARGET_B_IMPLEMENTATION_SUMMARY
  return [
    { label: 'Target B implementation', value: s.implementationStatus, sub: 'full engineering path drafted', tone: 'info' },
    { label: 'Execution', value: s.executionStatus, sub: 'no runtime, no execution', tone: 'danger' },
    { label: 'Production runtime', value: s.productionRuntime, sub: 'no approved sandbox model', tone: 'danger' },
    { label: 'WebUI execution', value: s.webuiExecution, sub: 'disabled — preview only', tone: 'danger' },
    { label: 'Remote registry', value: s.remoteRegistry, sub: 'disabled — no fetch', tone: 'danger' },
    { label: 'Marketplace', value: s.marketplace, sub: 'disabled — not reachable', tone: 'danger' },
    { label: 'Approval / authorization', value: s.approvalAuthorization, sub: 'no trust token provisioned', tone: 'danger' },
    { label: 'Production rollout', value: s.productionRollout, sub: 'no approved plan', tone: 'danger' },
    { label: 'P0 gates', value: s.p0Total, sub: '24 frozen gates', tone: 'info' },
    { label: 'P0 resolved', value: s.p0Resolved, sub: 'always 0 — requires human approval', tone: 'warn' },
    { label: 'Implementation layers', value: TARGET_B_IMPLEMENTATION_LAYERS.length, sub: 'all disabled', tone: 'info' },
    { label: 'Route governance', value: TARGET_B_IMPLEMENTATION_ROUTE_GOVERNANCE_BASELINE, sub: 'unchanged', tone: 'ok' },
  ]
}

/** Client-side layer filter options rendered as harmless client-side toggles. */
export const TARGET_B_LAYER_FILTER_OPTIONS: readonly {
  readonly key: TargetBLayerFilterKey
  readonly label: string
}[] = [
  { key: 'all', label: 'All layers' },
  { key: 'DESIGNED', label: 'Designed' },
  { key: 'SCAFFOLDED_DISABLED', label: 'Scaffolded (disabled)' },
]

/** Select the implementation layers matching a client-side status filter. Pure. */
export function filterTargetBImplementationLayers(
  filterKey: TargetBLayerFilterKey,
): readonly TargetBImplementationLayer[] {
  const layers = buildTargetBImplementationLayers()
  if (filterKey === 'all') return layers
  return layers.filter((l) => l.status === filterKey)
}

/**
 * A deterministic, redacted plain-text snapshot of the Target B implementation
 * summary, used by the Copy control. Pure — operates on the frozen projections
 * only, performs no network call and writes no file.
 */
export function buildTargetBImplementationSummaryText(): string {
  const s = TARGET_B_IMPLEMENTATION_SUMMARY
  const sig = TARGET_B_SIGNATURE_VERIFICATION
  const reg = TARGET_B_REGISTRY_TRUST
  const sb = TARGET_B_SANDBOX_BROKER
  const ap = TARGET_B_APPROVAL_GATE
  const ep = TARGET_B_EXECUTION_POLICY
  const ar = TARGET_B_AUDIT_ROLLBACK
  const lines = [
    `Hermes Dev WebUI — Target B End-to-End Implementation (${TARGET_B_IMPLEMENTATION_PHASE_LABEL})`,
    'GATED implementation scaffold — full engineering path drafted, every layer disabled. No execution, no approval, no authorization, no network, no new route.',
    `Target B: ${s.implementationStatus} — execution ${s.executionStatus}.`,
    `Production runtime: ${s.productionRuntime} | Arbitrary plugin loading: ${s.arbitraryPluginLoading} | Remote registry: ${s.remoteRegistry} | Marketplace: ${s.marketplace}`,
    `WebUI execution: ${s.webuiExecution} | Approval / authorization: ${s.approvalAuthorization} | Production rollout: ${s.productionRollout}`,
    `P0 gates: total ${s.p0Total} | partial ${s.p0PartialEvidence} | resolved ${s.p0Resolved} | pending human review ${s.p0PendingHumanReview} (${s.pendingHumanReviewGates.join(', ')}).`,
    `Implementation layers: ${TARGET_B_IMPLEMENTATION_LAYERS.length} drafted — every one disabled.`,
    `Signature verifier: production authorized ${sig.productionVerifierAuthorized} | fixture only ${sig.fixtureVerifierOnly} | trusted ${sig.trusted}.`,
    `Registry: mode ${reg.registryMode} | network ${reg.networkEnabled} | fetch ${reg.fetchEnabled} | marketplace ${reg.marketplaceEnabled}.`,
    `Sandbox broker: enabled ${sb.brokerEnabled} | execution ${sb.executionAllowed} | process spawn ${sb.processSpawnAllowed}.`,
    `Approval gate: human approval required ${ap.humanApprovalRequired} | trust token provisioned ${ap.trustTokenProvisioned} | fake accepted ${ap.fakeApprovalAccepted}.`,
    `Execution policy: allowed ${ep.allowed} | webui execute ${ep.webuiExecuteEnabled} | runtime route ${ep.runtimeRouteEnabled}.`,
    `Audit / rollback: persistence ${ar.auditPersistence} | kill switch ${ar.killSwitchReady} | production rollout ${ar.productionRollout}.`,
    `Route governance: ${TARGET_B_IMPLEMENTATION_ROUTE_GOVERNANCE_BASELINE} (unchanged).`,
    'Target B remains gated — Target A complete is prerequisite evidence only, it does NOT authorize Target B.',
  ]
  return lines.map((l) => redactTargetBImplementationValue(l)).join('\n')
}

/** Assemble the full read-only Target B Implementation view model. Deterministic. */
export function buildTargetBImplementationViewModel(): TargetBImplementationViewModel {
  return {
    schemaVersion: TARGET_B_IMPLEMENTATION_VERSION,
    phase: TARGET_B_IMPLEMENTATION_PHASE_LABEL,
    summary: buildTargetBImplementationSummary(),
    summaryCards: buildTargetBImplementationSummaryCards(),
    implementationLayers: buildTargetBImplementationLayers(),
    packageSchema: buildTargetBPackageSchema(),
    permissionModel: buildTargetBImplementationPermissionModel(),
    capabilityModel: buildTargetBCapabilityModel(),
    signatureVerification: buildTargetBSignatureVerification(),
    registryTrust: buildTargetBRegistryTrust(),
    sandboxBroker: buildTargetBSandboxBroker(),
    approvalGate: buildTargetBApprovalGate(),
    executionPolicy: buildTargetBExecutionPolicy(),
    auditRollback: buildTargetBAuditRollback(),
    enablementBlockers: buildTargetBImplementationBlockers(),
    statusBadges: buildTargetBImplementationStatusBadges(),
    boundaryItems: buildTargetBImplementationBoundaryItems(),
    forbiddenActions: buildTargetBImplementationForbiddenActions(),
    allowedUiActions: buildTargetBImplementationAllowedUiActions(),
    routeGovernanceBaseline: TARGET_B_IMPLEMENTATION_ROUTE_GOVERNANCE_BASELINE,
    backendRoutesChanged: false,
  }
}
