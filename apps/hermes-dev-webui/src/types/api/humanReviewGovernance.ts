/**
 * Human Review Governance read-only view-model types (Phase 3K).
 *
 * Pure, value-free TypeScript shapes for the Dev WebUI read-only surface that
 * unifies the P0 human-review / approval picture across the Phase 3 capability
 * chain. These types mirror the conservative, deterministic, redacted
 * projections emitted by the backend P0 evidence module
 * (hermes_cli/dev_web_p0_evidence.py) — they carry ONLY safe fields: no API
 * key, Authorization, Bearer, secret, callable repr, shell command, SQL
 * statement, production path, local plugin path, dynamic import path, external
 * URL, download URL, install command, or trust token.
 *
 * Nothing here grants permission, approves a gate, authorizes a runtime,
 * resolves a P0 gate, or performs a side effect. Every gate is unresolved; the
 * resolved count is frozen at 0; every authorization verdict is frozen NO-GO /
 * not-authorized. This surface is a decision-READINESS projection, not a
 * decision surface — it explains what code can prove vs what only an
 * out-of-band human review can approve.
 */

/** Schema version for the Human Review Governance envelope. */
export const HUMAN_REVIEW_SCHEMA_VERSION = 'phase-3k-human-review-governance-v1' as const

/** Frozen route-governance baseline (unchanged by this read-only surface). */
export const HUMAN_REVIEW_ROUTE_BASELINE = '34/34/5/0/1/1' as const

/**
 * Gate classification (mirrors backend GATE_STATUS_*). ``resolved`` is
 * intentionally NOT a member here — no gate is ever resolved on this surface.
 */
export type HumanReviewGateStatus =
  | 'partial_evidence'
  | 'blocked_by_human_review'
  | 'candidate_for_review'
  | 'governance_only'
  | 'no_evidence'

/** Human-readable label for a gate status (non-color identification). */
export interface HumanReviewGateStatusInfo {
  readonly status: HumanReviewGateStatus
  readonly label: string
}

/** Logical grouping of a P0 gate for the summary / table categories. */
export type HumanReviewGateCategory =
  | 'Runtime isolation'
  | 'Descriptor registry'
  | 'Sandbox guards'
  | 'Audit redaction'
  | 'Route governance'
  | 'Production safety'
  | 'Human approval'
  | 'Rollback / readiness'
  | 'Evidence reproducibility'

/** Strength of the evidence a gate currently carries (never "approved"). */
export type HumanReviewEvidenceLevel =
  | 'partial_code_evidence'
  | 'human_review_required'
  | 'governance_text_only'
  | 'no_evidence'

/** A single P0 gate projected for the Human Review Governance surface. */
export interface HumanReviewGate {
  readonly gateId: string
  readonly title: string
  readonly status: HumanReviewGateStatus
  readonly statusLabel: string
  readonly category: HumanReviewGateCategory
  readonly evidenceLevel: HumanReviewEvidenceLevel
  readonly requiresHumanReview: true
  readonly resolved: false
  readonly approved: false
  readonly blockedReason: string
  readonly codeEvidenceSummary: string
  readonly humanReviewRequirement: string
  readonly reviewerCategory: string
  readonly allowedNextAction: 'await_out_of_band_human_review'
  readonly forbiddenActions: readonly string[]
  readonly sourcePhase: string
  readonly relatedArtifacts: readonly string[]
  readonly productionAuthorizationImpact: 'NO-GO'
}

/** The conservative summary over the 24-gate registry. */
export interface HumanReviewSummary {
  readonly totalGates: 24
  readonly resolvedCount: 0
  readonly partialEvidenceCount: 19
  readonly pendingHumanReviewCount: 5
  readonly candidateForReviewCount: 0
  readonly governanceOnlyCount: 0
  readonly noEvidenceCount: 0
  readonly unresolvedCount: 24
  readonly implementationAuthorization: 'NO-GO'
  readonly phase3iProductionAuthorization: 'NOT_AUTHORIZED'
  readonly productionRuntimeAuthorization: 'NO-GO'
  readonly newRouteAuthorization: 'NO-GO'
  readonly productionRolloutAuthorization: 'NO-GO'
  readonly trustTokenProvisioned: false
  readonly classificationNote: string
}

/** A single evidence source in the Phase 3 capability-chain trail. */
export interface HumanReviewEvidenceSource {
  readonly phase: string
  readonly evidenceType: string
  readonly whatItProves: string
  readonly whatItDoesNotProve: string
  readonly authorizationImpact: 'Partial evidence only — no production authorization'
}

/** A frozen NO-GO decision dimension projected for display. */
export interface HumanReviewNogoDecision {
  readonly key: string
  readonly label: string
  readonly verdict: 'NO-GO' | 'NOT_AUTHORIZED'
  readonly reason: string
}

/** A relationship statement linking Runtime Governance to Human Review. */
export interface HumanReviewRelationshipItem {
  readonly key: string
  readonly label: string
  readonly detail: string
}

/** A frozen boundary-banner row (icon kind + explicit non-color text). */
export interface HumanReviewBoundaryItem {
  readonly kind: 'lock' | 'ban' | 'user'
  readonly label: string
}

/** A read-only status chip projected into the page header (non-color text). */
export interface HumanReviewStatusBadge {
  readonly label: string
}

/** A summary card projected for the Human Review Governance overview. */
export interface HumanReviewSummaryCard {
  readonly label: string
  readonly value: string | number
  readonly sub?: string
  readonly tone: 'ok' | 'warn' | 'danger' | 'info'
}

/** A client-side filter key for the gate table (operates on static data only). */
export type HumanReviewFilterKey =
  | 'all'
  | 'partial_evidence'
  | 'pending_human_review'
  | 'blocked_by_human_review'
  | 'governance_only'

/** A filter descriptor rendered as a harmless client-side toggle button. */
export interface HumanReviewFilterOption {
  readonly key: HumanReviewFilterKey
  readonly label: string
}

/** The full read-only Human Review Governance view model. */
export interface HumanReviewViewModel {
  readonly schemaVersion: typeof HUMAN_REVIEW_SCHEMA_VERSION
  readonly summary: HumanReviewSummary
  readonly gates: readonly HumanReviewGate[]
  readonly gateCount: 24
  readonly evidenceTrail: readonly HumanReviewEvidenceSource[]
  readonly nogoDecisions: readonly HumanReviewNogoDecision[]
  readonly runtimeRelationship: readonly HumanReviewRelationshipItem[]
  readonly forbiddenActions: readonly string[]
  readonly allowedUiActions: readonly string[]
  readonly routeGovernanceBaseline: typeof HUMAN_REVIEW_ROUTE_BASELINE
  readonly backendRoutesChanged: false
}
