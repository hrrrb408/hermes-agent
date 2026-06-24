/**
 * Governance Hub pure view-model projections (Phase 3L).
 *
 * Pure, deterministic, side-effect-free functions that turn the frozen static
 * manifest (@/constants/governanceHubManifest) into the read-only shapes the
 * Governance Hub section renders. No current time, no random id, no uuid, no
 * network fetch, no file read, no file write, no process spawn, no CLI call, no
 * backend call.
 *
 * Every projection is value-free and defense-in-depth redacted: a conservative
 * sanitizer masks any secret-shaped / production-path-shaped /
 * fake-approval-shaped substring so a future editor adding a secret or a fake
 * approval to the manifest can never leak it through this surface. The manifest
 * itself carries no secrets and no fake approvals today.
 */

import {
  GOVERNANCE_HUB_VERSION,
  GOVERNANCE_HUB_ROUTE_GOVERNANCE_BASELINE,
  GOVERNANCE_HUB_SUMMARY,
  GOVERNANCE_HUB_MODULES,
  GOVERNANCE_HUB_ROUTE_SUMMARY,
  GOVERNANCE_HUB_PRODUCTION_SAFETY,
  GOVERNANCE_HUB_DECISIONS,
  GOVERNANCE_HUB_DECISION_ROWS,
  GOVERNANCE_HUB_EVIDENCE_TRAIL,
  GOVERNANCE_HUB_DEFERRED_ITEMS,
  GOVERNANCE_HUB_CROSS_LINKS,
  GOVERNANCE_HUB_FORBIDDEN_ACTIONS,
  GOVERNANCE_HUB_ALLOWED_UI_ACTIONS,
  GOVERNANCE_HUB_STATUS_BADGES,
  GOVERNANCE_HUB_BOUNDARY_ITEMS,
} from '@/constants/governanceHubManifest'
import type {
  GovernanceHubViewModel,
  GovernanceHubSummary,
  GovernanceModuleStatus,
  GovernanceRouteSummary,
  GovernanceProductionSafety,
  GovernanceDecisionSummary,
  GovernanceDecisionRow,
  GovernanceEvidenceSource,
  GovernanceHubCrossLink,
  GovernanceBoundaryItem,
  GovernanceStatusBadge,
  GovernanceSummaryCard,
  GovernanceModuleLifecycle,
  GovernanceHubLinkTarget,
} from '@/types/api/governanceHub'

/**
 * Secret / production-path / fake-approval stems a defense-in-depth redactor
 * masks. These are *patterns* (not real values) — they exist only to scrub a
 * substring should one ever reach this surface. Mirrors the conservative spirit
 * of the backend redact_sandbox_payload: prefer masking over exposing.
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
]

/** Mask placeholder emitted by the defense-in-depth redactor. */
const REDACTED = '[REDACTED]'

/**
 * Defense-in-depth redactor. Masks any secret-shaped / production-path-shaped /
 * fake-approval-shaped substring in *value*. Pure and total — never throws,
 * never reads files or the network. Applied only to free-text fields projected
 * for display.
 */
export function redactGovernanceHubValue(value: string): string {
  if (typeof value !== 'string' || value.length === 0) return ''
  for (const stem of REDACT_STEMS) {
    if (value.toLowerCase().includes(stem.toLowerCase())) {
      // Mask the whole value once any stem matches — conservative.
      return REDACTED
    }
  }
  return value
}

/**
 * Stable public alias for {@link redactGovernanceHubValue}. Sanitizes free-text a
 * caller intends to display on the Governance Hub surface so a future editor
 * adding a secret-shaped / fake-approval-shaped substring can never leak it
 * through this view.
 */
export function sanitizeGovernanceHubDisplayText(value: string): string {
  return redactGovernanceHubValue(value)
}

/** True iff every decision verdict is NO-GO / not-authorized (the frozen invariant). */
const NO_GO_VERDICTS = new Set(['NO-GO', 'NOT_AUTHORIZED'])
export function everyDecisionHolds(
  decisions: readonly { verdict: string }[],
): boolean {
  return decisions.length > 0 && decisions.every((d) => NO_GO_VERDICTS.has(d.verdict))
}

/** True iff every module authorizes no production (authorization impact NO-GO). */
export function noModuleAuthorizesProduction(
  modules: readonly GovernanceModuleStatus[],
): boolean {
  return (
    modules.length > 0 &&
    modules.every((m) => m.authorizationImpact === 'NO-GO' && m.readOnly === true)
  )
}

/** Project the frozen summary (defensive copy). Deterministic. */
export function buildGovernanceHubSummary(): GovernanceHubSummary {
  return { ...GOVERNANCE_HUB_SUMMARY }
}

/**
 * Project the read-only module board (free-text fields defense-in-depth
 * redacted). Every nested collection is a fresh defensive copy, so mutating a
 * returned module can never reach the frozen canonical manifest.
 */
export function buildGovernanceHubModules(): readonly GovernanceModuleStatus[] {
  return GOVERNANCE_HUB_MODULES.map((m) => ({
    ...m,
    evidenceSummary: redactGovernanceHubValue(m.evidenceSummary),
    name: redactGovernanceHubValue(m.name),
  }))
}

/** Project the frozen route summary (defensive copy). Deterministic. */
export function buildGovernanceHubRouteSummary(): GovernanceRouteSummary {
  return { ...GOVERNANCE_HUB_ROUTE_SUMMARY }
}

/** Project the frozen production-safety block (defensive copy, note redacted). */
export function buildGovernanceHubProductionSafety(): GovernanceProductionSafety {
  return {
    ...GOVERNANCE_HUB_PRODUCTION_SAFETY,
    note: redactGovernanceHubValue(GOVERNANCE_HUB_PRODUCTION_SAFETY.note),
  }
}

/** Project the frozen decision block (defensive copy). Deterministic. */
export function buildGovernanceHubDecisions(): GovernanceDecisionSummary {
  return { ...GOVERNANCE_HUB_DECISIONS }
}

/** Project the frozen decision rows (defensive copy, free-text redacted). */
export function buildGovernanceHubDecisionRows(): readonly GovernanceDecisionRow[] {
  return GOVERNANCE_HUB_DECISION_ROWS.map((d) => ({
    ...d,
    reason: redactGovernanceHubValue(d.reason),
    label: redactGovernanceHubValue(d.label),
  }))
}

/** Project the frozen evidence trail (defensive copy, free-text redacted). */
export function buildGovernanceHubEvidenceTrail(): readonly GovernanceEvidenceSource[] {
  return GOVERNANCE_HUB_EVIDENCE_TRAIL.map((e) => ({
    ...e,
    completedDeliverable: redactGovernanceHubValue(e.completedDeliverable),
    whatItProves: redactGovernanceHubValue(e.whatItProves),
    whatItDoesNotProve: redactGovernanceHubValue(e.whatItDoesNotProve),
    evidenceType: redactGovernanceHubValue(e.evidenceType),
  }))
}

/** Project the frozen deferred list (defensive copy). */
export function buildGovernanceHubDeferredItems(): readonly string[] {
  return [...GOVERNANCE_HUB_DEFERRED_ITEMS]
}

/** Project the frozen cross-links (defensive copy, free-text redacted). */
export function buildGovernanceHubCrossLinks(): readonly GovernanceHubCrossLink[] {
  return GOVERNANCE_HUB_CROSS_LINKS.map((c) => ({
    target: c.target,
    label: redactGovernanceHubValue(c.label),
    detail: redactGovernanceHubValue(c.detail),
  }))
}

/** Project the forbidden-actions list (defensive copy). */
export function buildGovernanceHubForbiddenActions(): readonly string[] {
  return [...GOVERNANCE_HUB_FORBIDDEN_ACTIONS]
}

/** Project the allowed-UI-actions list (defensive copy). */
export function buildGovernanceHubAllowedUiActions(): readonly string[] {
  return [...GOVERNANCE_HUB_ALLOWED_UI_ACTIONS]
}

/** Project the frozen page-header status badges (defensive copy). */
export function buildGovernanceHubStatusBadges(): readonly GovernanceStatusBadge[] {
  return GOVERNANCE_HUB_STATUS_BADGES.map((b) => ({ label: b.label }))
}

/** Project the frozen boundary-banner rows (defensive copy, free-text redacted). */
export function buildGovernanceHubBoundaryItems(): readonly GovernanceBoundaryItem[] {
  return GOVERNANCE_HUB_BOUNDARY_ITEMS.map((row) => ({
    kind: row.kind,
    label: redactGovernanceHubValue(row.label),
  }))
}

/** Client-side module-status filter keys (operate on static data only). */
export type GovernanceModuleFilterKey = 'all' | GovernanceModuleLifecycle

/** The frozen module filter options rendered as harmless client-side toggles. */
export const GOVERNANCE_HUB_MODULE_FILTER_OPTIONS: readonly {
  readonly key: GovernanceModuleFilterKey
  readonly label: string
}[] = [
  { key: 'all', label: 'All modules' },
  { key: 'COMPLETE', label: 'Complete' },
  { key: 'IMPLEMENTED', label: 'Implemented' },
  { key: 'READ_ONLY', label: 'Read-only' },
]

/** Select the modules matching a client-side status filter. Pure — static data only. */
export function filterGovernanceHubModules(
  filterKey: GovernanceModuleFilterKey,
): readonly GovernanceModuleStatus[] {
  const modules = buildGovernanceHubModules()
  if (filterKey === 'all') return modules
  return modules.filter((m) => m.status === filterKey)
}

/**
 * Resolve a cross-link target to a DevConsole section id. Returns undefined for
 * unknown targets so the section can render an inert state. Pure — never calls
 * the nav store itself (the component wires the result to setSection).
 */
export function resolveCrossLinkTarget(
  target: GovernanceHubLinkTarget | string | null,
): GovernanceHubLinkTarget | undefined {
  if (target !== 'runtimeGovernance' && target !== 'humanReview') return undefined
  return target
}

/**
 * A deterministic, redacted plain-text snapshot of the control center summary,
 * used by the Copy control. Pure — operates on the frozen summary and route
 * projection only, performs no network call and writes no file.
 */
export function buildGovernanceHubSummaryText(): string {
  const s = GOVERNANCE_HUB_SUMMARY
  const r = GOVERNANCE_HUB_ROUTE_SUMMARY
  const lines = [
    `Hermes Dev WebUI — Governance Hub (${s.currentPhase})`,
    'READ-ONLY unified control center — no execution, no approval, no authorization, no new route.',
    '',
    `Runtime Governance: ${s.runtimeGovernanceStatus}`,
    `Human Review Governance: ${s.humanReviewGovernanceStatus}`,
    `Descriptor Registry: ${s.descriptorRegistryStatus}`,
    `Runtime Governance CLI: ${s.runtimeCliStatus}`,
    `Read-only WebUI: ${s.readOnlyWebuiStatus}`,
    '',
    `P0 gates: total ${s.p0Total} | resolved ${s.p0Resolved} | partial ${s.p0Partial} | pending human review ${s.p0PendingHumanReview}`,
    `Route governance: ${r.format} (OpenAPI ${r.openapiPaths} / Runtime ${r.runtimeRoutes} / GET ${r.toolGetRoutes} / write ${r.toolWriteHttpRoutes} / dry-run ${r.toolDryRunRoutes} / execute ${r.toolExecutionRoutes})`,
    `New backend route: ${r.newHttpRoutes} | New runtime route: ${r.newRuntimeRoutes} | New plugin route: ${r.newPluginRoutes}`,
    `Implementation Authorization: ${s.implementationAuthorization}`,
    `Production Runtime: ${s.productionRuntimeAuthorization}`,
    `Production Rollout: ${s.productionRollout}`,
  ]
  return lines.map((l) => redactGovernanceHubValue(l)).join('\n')
}

/** Summary cards for the Governance Hub overview. Deterministic. */
export function buildGovernanceHubSummaryCards(): readonly GovernanceSummaryCard[] {
  const s = GOVERNANCE_HUB_SUMMARY
  const r = GOVERNANCE_HUB_ROUTE_SUMMARY
  return [
    { label: 'Runtime Governance', value: s.runtimeGovernanceStatus, sub: 'Phase 3J read-only surface', tone: 'ok' },
    { label: 'Human Review Governance', value: s.humanReviewGovernanceStatus, sub: 'Phase 3K read-only surface', tone: 'ok' },
    { label: 'P0 gates', value: s.p0Total, sub: '24 frozen gates', tone: 'info' },
    { label: 'P0 resolved', value: s.p0Resolved, sub: 'always 0 — requires human approval', tone: 'warn' },
    { label: 'Pending human review', value: s.p0PendingHumanReview, sub: 'blocked_by_human_review', tone: 'danger' },
    { label: 'Route governance', value: r.format, sub: 'OpenAPI / Runtime / GET / write / dry-run / execute', tone: 'ok' },
    { label: 'Production runtime', value: s.productionRuntimeAuthorization, sub: 'no approved sandbox model', tone: 'danger' },
    { label: 'Production rollout', value: s.productionRollout, sub: 'no trust token provisioned', tone: 'danger' },
    { label: 'Backend route changes', value: r.newHttpRoutes, sub: 'no backend route added', tone: 'ok' },
    { label: 'Side effects', value: 'all false', sub: 'frozen no-side-effect surface', tone: 'ok' },
  ]
}

/** Assemble the full read-only Governance Hub view model. Deterministic. */
export function buildGovernanceHubViewModel(): GovernanceHubViewModel {
  return {
    schemaVersion: GOVERNANCE_HUB_VERSION,
    summary: buildGovernanceHubSummary(),
    modules: buildGovernanceHubModules(),
    routeSummary: buildGovernanceHubRouteSummary(),
    productionSafety: buildGovernanceHubProductionSafety(),
    decisions: buildGovernanceHubDecisions(),
    decisionRows: buildGovernanceHubDecisionRows(),
    evidenceTrail: buildGovernanceHubEvidenceTrail(),
    deferredItems: buildGovernanceHubDeferredItems(),
    crossLinks: buildGovernanceHubCrossLinks(),
    forbiddenActions: buildGovernanceHubForbiddenActions(),
    allowedUiActions: buildGovernanceHubAllowedUiActions(),
    routeGovernanceBaseline: GOVERNANCE_HUB_ROUTE_GOVERNANCE_BASELINE,
    backendRoutesChanged: false,
  }
}
