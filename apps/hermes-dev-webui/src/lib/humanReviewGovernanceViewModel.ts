/**
 * Human Review Governance pure view-model projections (Phase 3K).
 *
 * Pure, deterministic, side-effect-free functions that turn the frozen static
 * manifest (@/constants/humanReviewGovernanceManifest) into the read-only shapes
 * the Human Review Governance section renders. No current time, no random id,
 * no uuid, no network fetch, no file read, no file write, no process spawn, no
 * CLI call, no backend call.
 *
 * Every projection is value-free and defense-in-depth redacted: a conservative
 * sanitizer masks any secret-shaped / production-path-shaped /
 * fake-approval-shaped substring so a future editor adding a secret or a fake
 * approval to the manifest can never leak it through this surface. The manifest
 * itself carries no secrets and no fake approvals today.
 */

import {
  HUMAN_REVIEW_VERSION,
  HUMAN_REVIEW_ROUTE_GOVERNANCE_BASELINE,
  HUMAN_REVIEW_GATES,
  HUMAN_REVIEW_SUMMARY,
  HUMAN_REVIEW_EVIDENCE_TRAIL,
  HUMAN_REVIEW_NOGO_DECISIONS,
  HUMAN_REVIEW_RUNTIME_RELATIONSHIP,
  HUMAN_REVIEW_FORBIDDEN_ACTIONS,
  HUMAN_REVIEW_ALLOWED_UI_ACTIONS,
  HUMAN_REVIEW_STATUS_BADGES,
  HUMAN_REVIEW_BOUNDARY_ITEMS,
} from '@/constants/humanReviewGovernanceManifest'
import type {
  HumanReviewViewModel,
  HumanReviewGate,
  HumanReviewSummary,
  HumanReviewEvidenceSource,
  HumanReviewNogoDecision,
  HumanReviewRelationshipItem,
  HumanReviewBoundaryItem,
  HumanReviewStatusBadge,
  HumanReviewSummaryCard,
  HumanReviewFilterKey,
  HumanReviewFilterOption,
} from '@/types/api/humanReviewGovernance'

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
export function redactHumanReviewValue(value: string): string {
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
 * Stable public alias for {@link redactHumanReviewValue}. Sanitizes free-text a
 * caller intends to display on the Human Review Governance surface so a future
 * editor adding a secret-shaped / fake-approval-shaped substring can never leak
 * it through this view.
 */
export function sanitizeHumanReviewDisplayText(value: string): string {
  return redactHumanReviewValue(value)
}

/** The default gate selected on first render — a pending-human-review gate. */
export const DEFAULT_GATE_ID = 'P0-15'

/**
 * Project the read-only gate rows (free-text fields defense-in-depth redacted).
 * Every nested collection is a fresh defensive copy, so mutating a returned gate
 * (or its forbiddenActions / relatedArtifacts) can never reach the frozen
 * canonical manifest.
 */
export function buildHumanReviewGates(): readonly HumanReviewGate[] {
  return HUMAN_REVIEW_GATES.map((g) => ({
    ...g,
    blockedReason: redactHumanReviewValue(g.blockedReason),
    codeEvidenceSummary: redactHumanReviewValue(g.codeEvidenceSummary),
    humanReviewRequirement: redactHumanReviewValue(g.humanReviewRequirement),
    title: redactHumanReviewValue(g.title),
    forbiddenActions: [...g.forbiddenActions],
    relatedArtifacts: [...g.relatedArtifacts],
  }))
}

/** Look up a gate by id (membership only; returns undefined if absent). */
export function findHumanReviewGate(
  gateId: string | null,
): HumanReviewGate | undefined {
  if (!gateId) return undefined
  return HUMAN_REVIEW_GATES.find((g) => g.gateId === gateId)
}

/** The frozen filter options rendered as harmless client-side toggle buttons. */
export const HUMAN_REVIEW_FILTER_OPTIONS: readonly HumanReviewFilterOption[] = [
  { key: 'all', label: 'All gates' },
  { key: 'partial_evidence', label: 'Partial evidence' },
  { key: 'pending_human_review', label: 'Pending human review' },
  { key: 'blocked_by_human_review', label: 'Blocked by human review' },
  { key: 'governance_only', label: 'Governance-only / no evidence' },
]

/**
 * Select the gates matching a client-side filter. Pure — operates on static
 * data only, never fetches. ``pending_human_review`` and
 * ``blocked_by_human_review`` both select the 5 ``blocked_by_human_review``
 * gates (the only set only a human action can advance).
 */
export function filterHumanReviewGates(
  filterKey: HumanReviewFilterKey,
): readonly HumanReviewGate[] {
  const gates = buildHumanReviewGates()
  if (filterKey === 'all') return gates
  if (filterKey === 'pending_human_review' || filterKey === 'blocked_by_human_review') {
    return gates.filter((g) => g.status === 'blocked_by_human_review')
  }
  if (filterKey === 'partial_evidence') {
    return gates.filter((g) => g.status === 'partial_evidence')
  }
  // governance_only: candidate_for_review / governance_only / no_evidence
  return gates.filter(
    (g) =>
      g.status === 'governance_only' ||
      g.status === 'no_evidence' ||
      g.status === 'candidate_for_review',
  )
}

/** Project the frozen summary (defensive copy). Deterministic. */
export function buildHumanReviewSummary(): HumanReviewSummary {
  return { ...HUMAN_REVIEW_SUMMARY }
}

/** Summary cards for the Human Review Governance overview. Deterministic. */
export function buildHumanReviewSummaryCards(): readonly HumanReviewSummaryCard[] {
  const s = HUMAN_REVIEW_SUMMARY
  return [
    {
      label: 'Total P0 gates',
      value: s.totalGates,
      sub: '24 frozen gates',
      tone: 'info',
    },
    {
      label: 'Resolved',
      value: s.resolvedCount,
      sub: 'always 0 — requires human approval',
      tone: 'warn',
    },
    {
      label: 'Partial evidence',
      value: s.partialEvidenceCount,
      sub: 'real code/test evidence, not approved',
      tone: 'warn',
    },
    {
      label: 'Pending human review',
      value: s.pendingHumanReviewCount,
      sub: 'blocked_by_human_review',
      tone: 'danger',
    },
    {
      label: 'Governance-only',
      value: s.governanceOnlyCount,
      sub: 'no evidence-only gates',
      tone: 'info',
    },
    {
      label: 'Implementation Authorization',
      value: s.implementationAuthorization,
      sub: 'P0-15 pending project owner',
      tone: 'danger',
    },
    {
      label: 'Production runtime',
      value: s.productionRuntimeAuthorization,
      sub: 'no approved sandbox model',
      tone: 'danger',
    },
    {
      label: 'Production rollout',
      value: s.productionRolloutAuthorization,
      sub: 'no trust token provisioned',
      tone: 'danger',
    },
    {
      label: 'Backend routes changed',
      value: 'no',
      sub: HUMAN_REVIEW_ROUTE_GOVERNANCE_BASELINE,
      tone: 'ok',
    },
  ]
}

/** Project the frozen evidence trail (defensive copy, free-text redacted). */
export function buildHumanReviewEvidenceTrail(): readonly HumanReviewEvidenceSource[] {
  return HUMAN_REVIEW_EVIDENCE_TRAIL.map((e) => ({
    ...e,
    whatItProves: redactHumanReviewValue(e.whatItProves),
    whatItDoesNotProve: redactHumanReviewValue(e.whatItDoesNotProve),
    evidenceType: redactHumanReviewValue(e.evidenceType),
  }))
}

/** Project the frozen NO-GO decisions (defensive copy, free-text redacted). */
export function buildHumanReviewNogoDecisions(): readonly HumanReviewNogoDecision[] {
  return HUMAN_REVIEW_NOGO_DECISIONS.map((d) => ({ ...d, reason: redactHumanReviewValue(d.reason) }))
}

/** Project the frozen runtime-relationship rows (defensive copy, redacted). */
export function buildHumanReviewRuntimeRelationship(): readonly HumanReviewRelationshipItem[] {
  return HUMAN_REVIEW_RUNTIME_RELATIONSHIP.map((r) => ({
    ...r,
    detail: redactHumanReviewValue(r.detail),
  }))
}

/** Project the forbidden-actions list (defensive copy). */
export function buildHumanReviewForbiddenActions(): readonly string[] {
  return [...HUMAN_REVIEW_FORBIDDEN_ACTIONS]
}

/** Project the allowed-UI-actions list (defensive copy). */
export function buildHumanReviewAllowedUiActions(): readonly string[] {
  return [...HUMAN_REVIEW_ALLOWED_UI_ACTIONS]
}

/** Project the frozen page-header status badges (defensive copy). */
export function buildHumanReviewStatusBadges(): readonly HumanReviewStatusBadge[] {
  return HUMAN_REVIEW_STATUS_BADGES.map((b) => ({ label: b.label }))
}

/** Project the frozen boundary-banner rows (defensive copy). */
export function buildHumanReviewBoundaryItems(): readonly HumanReviewBoundaryItem[] {
  return HUMAN_REVIEW_BOUNDARY_ITEMS.map((row) => ({
    kind: row.kind,
    label: redactHumanReviewValue(row.label),
  }))
}

/** Assemble the full read-only Human Review Governance view model. Deterministic. */
export function buildHumanReviewViewModel(): HumanReviewViewModel {
  const gates = buildHumanReviewGates()
  return {
    schemaVersion: HUMAN_REVIEW_VERSION,
    summary: buildHumanReviewSummary(),
    gates,
    gateCount: 24,
    evidenceTrail: buildHumanReviewEvidenceTrail(),
    nogoDecisions: buildHumanReviewNogoDecisions(),
    runtimeRelationship: buildHumanReviewRuntimeRelationship(),
    forbiddenActions: buildHumanReviewForbiddenActions(),
    allowedUiActions: buildHumanReviewAllowedUiActions(),
    routeGovernanceBaseline: HUMAN_REVIEW_ROUTE_GOVERNANCE_BASELINE,
    backendRoutesChanged: false,
  }
}

/** True iff every gate is unresolved and every NO-GO decision is NO-GO / not-authorized. */
const NO_GO_VERDICTS = new Set(['NO-GO', 'NOT_AUTHORIZED'])
export function everyGateUnresolved(gates: readonly HumanReviewGate[]): boolean {
  return gates.length > 0 && gates.every((g) => g.resolved === false && g.approved === false)
}
export function everyNogoDecisionHolds(
  decisions: readonly HumanReviewNogoDecision[],
): boolean {
  return decisions.length > 0 && decisions.every((d) => NO_GO_VERDICTS.has(d.verdict))
}
