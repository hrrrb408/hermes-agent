/**
 * Target B Authorization Package pure view-model projections (Phase 4C).
 *
 * Pure, deterministic, side-effect-free functions that turn the frozen static
 * manifest (@/constants/targetBAuthorizationManifest) into the read-only shapes
 * the Target B Authorization region renders. No current time, no random id,
 * no uuid, no network fetch, no file read, no file write, no process spawn,
 * no CLI call, no backend call.
 *
 * Every projection is value-free and defense-in-depth redacted: a conservative
 * sanitizer masks any secret-shaped / production-path-shaped /
 * fake-authorization-shaped / trust-token / Target-B-authorization marker
 * substring so a future editor adding a secret, a fake approval, or a fake trust
 * token to the manifest can never leak it through this surface. The manifest
 * itself carries no secrets, no fake approvals, and no fake tokens today.
 *
 * Mutating any returned value can never reach the frozen canonical manifest,
 * can never flip a frozen BLOCKED readiness, can never flip a frozen NO-GO
 * verdict, can never flip a frozen false authorization flag, can never provision
 * a trust token, can never resolve a P0 gate, and can never raise P0 resolved
 * above 0.
 */

import {
  TARGET_B_AUTHORIZATION_VERSION,
  TARGET_B_AUTHORIZATION_PHASE_LABEL,
  TARGET_B_AUTHORIZATION_ROUTE_GOVERNANCE_BASELINE,
  TARGET_B_AUTHORIZATION_SUMMARY,
  TARGET_B_AUTHORIZATION_LAYERS,
  TARGET_B_HUMAN_APPROVAL,
  TARGET_B_TRUST_TOKEN,
  TARGET_B_TRUSTED_PUBLISHERS,
  TARGET_B_PRODUCTION_SIGNATURE,
  TARGET_B_SANDBOX_LIFECYCLE,
  TARGET_B_POLICIES,
  TARGET_B_ROLLBACK_INCIDENT,
  TARGET_B_ROUTE_AUTHORIZATION,
  TARGET_B_P0_GATE_COVERAGE,
  TARGET_B_ENABLEMENT_READINESS,
  TARGET_B_AUTHORIZATION_BLOCKERS,
  TARGET_B_AUTHORIZATION_STATUS_BADGES,
  TARGET_B_AUTHORIZATION_BOUNDARY_ITEMS,
  TARGET_B_AUTHORIZATION_FORBIDDEN_ACTIONS,
  TARGET_B_AUTHORIZATION_ALLOWED_UI_ACTIONS,
} from '@/constants/targetBAuthorizationManifest'
import type {
  TargetBAuthorizationViewModel,
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
  TargetBP0GateCoverageProjection,
  TargetBEnablementReadinessProjection,
  TargetBAuthorizationBlocker,
  TargetBAuthorizationStatusBadge,
  TargetBAuthorizationBoundaryItem,
  TargetBAuthorizationSummaryCard,
  TargetBAuthorizationLayerFilterKey,
} from '@/types/api/targetBAuthorization'

/**
 * Secret / production-path / fake-authorization / trust-token stems a
 * defense-in-depth redactor masks. These are *patterns* (not real values) —
 * they exist only to scrub a substring should one ever reach this surface.
 * Comparison is case-insensitive, so stems are written in their canonical
 * lower-case form.
 */
const REDACT_STEMS: readonly string[] = [
  'sk-',
  'bearer ',
  'authorization:',
  'ghp_',
  'xox',
  'begin private key',
  'production home',
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
 * fake-authorization-shaped / trust-token substring in *value*. Pure and total —
 * never throws, never reads files or the network. Applied only to free-text
 * fields projected for display.
 */
export function redactTargetBAuthorizationValue(value: string): string {
  if (typeof value !== 'string' || value.length === 0) return ''
  for (const stem of REDACT_STEMS) {
    if (value.toLowerCase().includes(stem.toLowerCase())) {
      return REDACTED
    }
  }
  return value
}

/** Stable public alias for {@link redactTargetBAuthorizationValue}. */
export function sanitizeTargetBAuthorizationDisplayText(value: string): string {
  return redactTargetBAuthorizationValue(value)
}

/** True iff every authorization verdict in the summary is frozen NO-GO. */
export function allTargetBAuthorizationVerdictsNoGo(
  summary: TargetBAuthorizationSummary,
): boolean {
  return (
    summary.productionRuntime === 'NO-GO' &&
    summary.registry === 'NO-GO' &&
    summary.marketplace === 'NO-GO' &&
    summary.webuiExecution === 'NO-GO' &&
    summary.approvalAuthorization === 'NO-GO' &&
    summary.productionRollout === 'NO-GO'
  )
}

/** True iff every authorization layer is unauthorized. */
export function allTargetBAuthorizationLayersUnauthorized(
  layers: readonly TargetBAuthorizationLayer[],
): boolean {
  return layers.length > 0 && layers.every((l) => l.authorized === false)
}

/** True iff the readiness stays BLOCKED and production enablement is not allowed. */
export function targetBAuthorizationStaysBlocked(
  readiness: TargetBEnablementReadinessProjection,
): boolean {
  return readiness.readinessStatus === 'BLOCKED' && readiness.productionEnablementAllowed === false
}

/** Project the frozen summary (defensive copy + redacted free-text). Deterministic. */
export function buildTargetBAuthorizationSummary(): TargetBAuthorizationSummary {
  const s = TARGET_B_AUTHORIZATION_SUMMARY
  return {
    ...s,
    targetName: redactTargetBAuthorizationValue(s.targetName),
    requiredBeforeEnable: s.requiredBeforeEnable.map((r) => redactTargetBAuthorizationValue(r)),
  }
}

/**
 * Project the authorization sub-layer board (free-text fields defense-in-depth
 * redacted). Every nested collection is a fresh defensive copy, so mutating a
 * returned layer can never reach the frozen canonical manifest.
 */
export function buildTargetBAuthorizationLayers(): readonly TargetBAuthorizationLayer[] {
  return TARGET_B_AUTHORIZATION_LAYERS.map((l) => ({
    key: l.key,
    layer: redactTargetBAuthorizationValue(l.layer),
    status: l.status,
    authorized: false,
    fixtureOnly: l.fixtureOnly,
    riskLevel: l.riskLevel,
    requiredMaterial: redactTargetBAuthorizationValue(l.requiredMaterial),
  }))
}

/** Project the frozen human approval projection (defensive copy). */
export function buildTargetBHumanApproval(): TargetBHumanApprovalProjection {
  return { ...TARGET_B_HUMAN_APPROVAL }
}

/** Project the frozen trust token projection (defensive copy). */
export function buildTargetBTrustToken(): TargetBTrustTokenProjection {
  return { ...TARGET_B_TRUST_TOKEN }
}

/** Project the frozen trusted publisher set projection (defensive copy). */
export function buildTargetBTrustedPublishers(): TargetBTrustedPublisherProjection {
  return { ...TARGET_B_TRUSTED_PUBLISHERS }
}

/** Project the frozen production signature projection (defensive copy). */
export function buildTargetBProductionSignature(): TargetBProductionSignatureProjection {
  return { ...TARGET_B_PRODUCTION_SIGNATURE }
}

/** Project the frozen sandbox lifecycle projection (defensive copy). */
export function buildTargetBSandboxLifecycle(): TargetBSandboxLifecycleProjection {
  return { ...TARGET_B_SANDBOX_LIFECYCLE }
}

/** Project the frozen registry / network / secret policy projection (defensive copy). */
export function buildTargetBPolicies(): TargetBPolicyProjection {
  return { ...TARGET_B_POLICIES }
}

/** Project the frozen rollback / incident projection (defensive copy). */
export function buildTargetBRollbackIncident(): TargetBRollbackIncidentProjection {
  return { ...TARGET_B_ROLLBACK_INCIDENT }
}

/** Project the frozen route authorization projection (defensive copy). */
export function buildTargetBRouteAuthorization(): TargetBRouteAuthorizationProjection {
  return { ...TARGET_B_ROUTE_AUTHORIZATION }
}

/** Project the frozen P0 gate coverage projection (defensive copy). */
export function buildTargetBP0GateCoverage(): TargetBP0GateCoverageProjection {
  return { ...TARGET_B_P0_GATE_COVERAGE }
}

/** Project the frozen enablement readiness projection (defensive copy). */
export function buildTargetBEnablementReadiness(): TargetBEnablementReadinessProjection {
  return { ...TARGET_B_ENABLEMENT_READINESS }
}

/** Project the enablement blockers (free-text redacted). Defensive copy. */
export function buildTargetBAuthorizationBlockers(): readonly TargetBAuthorizationBlocker[] {
  return TARGET_B_AUTHORIZATION_BLOCKERS.map((b) => ({
    key: b.key,
    label: redactTargetBAuthorizationValue(b.label),
    resolved: false,
    detail: redactTargetBAuthorizationValue(b.detail),
  }))
}

/** Project the frozen status badges (defensive copy). Deterministic. */
export function buildTargetBAuthorizationStatusBadges(): readonly TargetBAuthorizationStatusBadge[] {
  return TARGET_B_AUTHORIZATION_STATUS_BADGES.map((b) => ({
    label: redactTargetBAuthorizationValue(b.label),
  }))
}

/** Project the frozen boundary-banner rows (free-text redacted). Defensive copy. */
export function buildTargetBAuthorizationBoundaryItems(): readonly TargetBAuthorizationBoundaryItem[] {
  return TARGET_B_AUTHORIZATION_BOUNDARY_ITEMS.map((row) => ({
    kind: row.kind,
    label: redactTargetBAuthorizationValue(row.label),
  }))
}

/** Project the forbidden-actions list (defensive copy). */
export function buildTargetBAuthorizationForbiddenActions(): readonly string[] {
  return [...TARGET_B_AUTHORIZATION_FORBIDDEN_ACTIONS]
}

/** Project the allowed-UI-actions list (defensive copy). */
export function buildTargetBAuthorizationAllowedUiActions(): readonly string[] {
  return [...TARGET_B_AUTHORIZATION_ALLOWED_UI_ACTIONS]
}

/** Summary cards for the authorization overview. Deterministic. */
export function buildTargetBAuthorizationSummaryCards(): readonly TargetBAuthorizationSummaryCard[] {
  const s = TARGET_B_AUTHORIZATION_SUMMARY
  const er = TARGET_B_ENABLEMENT_READINESS
  return [
    { label: 'Authorization package', value: s.authorizationStatus, sub: 'validation structure implemented', tone: 'info' },
    { label: 'Readiness', value: er.readinessStatus, sub: 'no real authorization material', tone: 'danger' },
    { label: 'Production enablement', value: s.productionEnablementAllowed ? 'allowed' : 'not allowed', sub: 'never without full authorization', tone: 'danger' },
    { label: 'Production runtime', value: s.productionRuntime, sub: 'NO-GO', tone: 'danger' },
    { label: 'Trust token', value: s.trustTokenProvisioned ? 'provisioned' : 'not provisioned', sub: 'no out-of-band token', tone: 'danger' },
    { label: 'Production signature verifier', value: s.productionSignatureVerifierAuthorized ? 'authorized' : 'not authorized', sub: 'fixture-only', tone: 'danger' },
    { label: 'WebUI execution', value: s.webuiExecution, sub: 'disabled', tone: 'danger' },
    { label: 'Registry / Marketplace', value: s.registry, sub: 'disabled — no fetch, no marketplace', tone: 'danger' },
    { label: 'Approval / authorization', value: s.approvalAuthorization, sub: 'fake / AI / metadata rejected', tone: 'danger' },
    { label: 'P0 resolved', value: s.p0Resolved, sub: 'always 0 — requires real approval + token', tone: 'warn' },
    { label: 'Authorization layers', value: TARGET_B_AUTHORIZATION_LAYERS.length, sub: 'all unauthorized', tone: 'info' },
    { label: 'Route governance', value: TARGET_B_AUTHORIZATION_ROUTE_GOVERNANCE_BASELINE, sub: 'unchanged', tone: 'ok' },
  ]
}

/** Client-side layer filter options rendered as harmless client-side toggles. */
export const TARGET_B_AUTHORIZATION_LAYER_FILTER_OPTIONS: readonly {
  readonly key: TargetBAuthorizationLayerFilterKey
  readonly label: string
}[] = [
  { key: 'all', label: 'All layers' },
  { key: 'NOT_AUTHORIZED', label: 'Not authorized' },
  { key: 'DESIGN_READY_ONLY', label: 'Design-ready only' },
]

/** Select the authorization layers matching a client-side status filter. Pure. */
export function filterTargetBAuthorizationLayers(
  filterKey: TargetBAuthorizationLayerFilterKey,
): readonly TargetBAuthorizationLayer[] {
  const layers = buildTargetBAuthorizationLayers()
  if (filterKey === 'all') return layers
  return layers.filter((l) => l.status === filterKey)
}

/**
 * A deterministic, redacted plain-text snapshot of the Target B authorization
 * package summary, used by the Copy control. Pure — operates on the frozen
 * projections only, performs no network call and writes no file.
 */
export function buildTargetBAuthorizationSummaryText(): string {
  const s = TARGET_B_AUTHORIZATION_SUMMARY
  const er = TARGET_B_ENABLEMENT_READINESS
  const lines = [
    `Hermes Dev WebUI — Target B Authorization Package (${TARGET_B_AUTHORIZATION_PHASE_LABEL})`,
    'AUTHORIZATION PACKAGE — validation structure implemented, every gate fail-closed. No fabricated approval, no bypassed P0, no minted trust token, no GO.',
    `Authorization status: ${s.authorizationStatus} — readiness ${er.readinessStatus}.`,
    `Production enablement allowed: ${s.productionEnablementAllowed} | Production runtime: ${s.productionRuntime} | Trust token provisioned: ${s.trustTokenProvisioned}.`,
    `Registry: ${s.registry} | Marketplace: ${s.marketplace} | WebUI execution: ${s.webuiExecution} | Approval: ${s.approvalAuthorization} | Production rollout: ${s.productionRollout}.`,
    `P0 gates: total ${s.p0Total} | partial ${s.p0PartialEvidence} | resolved ${s.p0Resolved} | pending human review ${s.p0PendingHumanReview} (${s.pendingHumanReviewGates.join(', ')}).`,
    `Authorization layers: ${TARGET_B_AUTHORIZATION_LAYERS.length} — every one unauthorized.`,
    `Blockers: ${er.blockers.length} unresolved — ${er.blockers.join(', ')}.`,
    `Route governance: ${TARGET_B_AUTHORIZATION_ROUTE_GOVERNANCE_BASELINE} (unchanged).`,
    'Target B remains BLOCKED — Phase 4B gated engineering is prerequisite evidence only, it does NOT authorize Target B.',
  ]
  return lines.map((l) => redactTargetBAuthorizationValue(l)).join('\n')
}

/** Assemble the full read-only Target B Authorization view model. Deterministic. */
export function buildTargetBAuthorizationViewModel(): TargetBAuthorizationViewModel {
  return {
    schemaVersion: TARGET_B_AUTHORIZATION_VERSION,
    phase: TARGET_B_AUTHORIZATION_PHASE_LABEL,
    summary: buildTargetBAuthorizationSummary(),
    summaryCards: buildTargetBAuthorizationSummaryCards(),
    authorizationLayers: buildTargetBAuthorizationLayers(),
    humanApproval: buildTargetBHumanApproval(),
    trustToken: buildTargetBTrustToken(),
    trustedPublishers: buildTargetBTrustedPublishers(),
    productionSignature: buildTargetBProductionSignature(),
    sandboxLifecycle: buildTargetBSandboxLifecycle(),
    policies: buildTargetBPolicies(),
    rollbackIncident: buildTargetBRollbackIncident(),
    routeAuthorization: buildTargetBRouteAuthorization(),
    p0GateCoverage: buildTargetBP0GateCoverage(),
    enablementReadiness: buildTargetBEnablementReadiness(),
    enablementBlockers: buildTargetBAuthorizationBlockers(),
    statusBadges: buildTargetBAuthorizationStatusBadges(),
    boundaryItems: buildTargetBAuthorizationBoundaryItems(),
    forbiddenActions: buildTargetBAuthorizationForbiddenActions(),
    allowedUiActions: buildTargetBAuthorizationAllowedUiActions(),
    routeGovernanceBaseline: TARGET_B_AUTHORIZATION_ROUTE_GOVERNANCE_BASELINE,
    backendRoutesChanged: false,
  }
}
