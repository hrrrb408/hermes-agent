/**
 * Frozen static Human Review Governance manifest — Phase 3K (frontend mirror).
 *
 * A tracked, reviewable, deterministic mirror of the P0 human-review / approval
 * picture across the Phase 3 capability chain. It is the read-only data source
 * for the Dev WebUI Human Review Governance section. It carries ONLY safe,
 * value-free fields — no API key, Authorization, Bearer, secret, callable repr,
 * shell command, SQL statement, production path, local plugin path, dynamic
 * import path, external URL, download URL, install command, or trust token.
 *
 * Provenance: derived from the frozen backend constants in
 *   - hermes_cli/dev_web_p0_evidence.py  (24-gate registry, classifications,
 *     reviewers, resolution requirements, frozen NO-GO / not-authorized flags)
 *   - hermes_cli/dev_web_safety_baseline.py  (route-governance baseline)
 *
 * Gate titles, classifications, reviewer categories, and resolution
 * requirements mirror the backend P0 gate registry verbatim. The 5
 * ``blocked_by_human_review`` gates are the gates only an out-of-band human /
 * project-owner action can advance; the 19 ``partial_evidence`` gates carry
 * real code/test evidence but are not approved. No gate is resolved.
 *
 * The WebUI does NOT call the CLI, does NOT run the Python runtime, does NOT
 * spawn a process, does NOT fetch remote data, does NOT read or write files,
 * and does NOT access production or ~/.hermes. Every value here is static and
 * deterministic — no current time, no random id, no uuid, no network fetch.
 *
 * This manifest describes the human-review / decision-readiness state only — it
 * never grants permission, never approves a gate, never authorizes production,
 * never signs off, and never resolves a P0 gate. resolvedCount stays 0 and every
 * authorization verdict stays NO-GO / not-authorized no matter what renders.
 */

import type {
  HumanReviewGate,
  HumanReviewSummary,
  HumanReviewEvidenceSource,
  HumanReviewNogoDecision,
  HumanReviewRelationshipItem,
  HumanReviewBoundaryItem,
  HumanReviewStatusBadge,
  HUMAN_REVIEW_ROUTE_BASELINE,
} from '@/types/api/humanReviewGovernance'

/**
 * Recursively deep-freeze a value (arrays + nested objects). Applied to every
 * exported constant so the canonical human-review state is immutable at runtime
 * — an external caller can never mutate a returned projection into the canonical
 * manifest, never flip a frozen NO-GO verdict, and never flip a frozen
 * unresolved / not-approved gate. Reads, spreads, and `.map()` copies are
 * unaffected. Pure and total.
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

/** Schema version (mirrors HUMAN_REVIEW_SCHEMA_VERSION). */
export const HUMAN_REVIEW_VERSION = deepFreeze('phase-3k-human-review-governance-v1')

/** Frozen route-governance baseline (unchanged by this read-only surface). */
export const HUMAN_REVIEW_ROUTE_GOVERNANCE_BASELINE: typeof HUMAN_REVIEW_ROUTE_BASELINE = '34/34/5/0/1/1'

/**
 * The frozen 24-gate registry (mirrors backend hermes_cli/dev_web_p0_evidence.py
 * GATES). Every gate is unresolved; 19 are partial_evidence and 5 are
 * blocked_by_human_review. No gate is resolved, none is approved, and the
 * production authorization impact of every gate is NO-GO. Titles, reviewers,
 * and resolution requirements mirror the backend verbatim.
 */
export const HUMAN_REVIEW_GATES: readonly HumanReviewGate[] = deepFreeze([
  {
    gateId: 'P0-01',
    title: 'Sandbox model',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Sandbox guards',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Skeleton exists; not an approved runtime sandbox model.',
    codeEvidenceSummary: 'dev_web_sandbox_proof.py skeleton + adversarial proof tests.',
    humanReviewRequirement: 'Approved sandbox model plus sandbox trust proof.',
    reviewerCategory: 'security reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'enable runtime'],
    sourcePhase: 'Phase 3H proof runner',
    relatedArtifacts: ['dev_web_sandbox_proof.py', 'test_dev_web_phase_3h_sandbox_proof_skeleton.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-02',
    title: 'Process isolation',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Runtime isolation',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'process.spawn denied; no approved process-isolation model.',
    codeEvidenceSummary: 'dev_web_sandbox_policy.py denies process spawn.',
    humanReviewRequirement: 'Approved process-isolation model.',
    reviewerCategory: 'security reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'enable runtime'],
    sourcePhase: 'Phase 3H proof runner',
    relatedArtifacts: ['dev_web_sandbox_policy.py', 'test_dev_web_phase_3h_sandbox_proof_skeleton.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-03',
    title: 'Filesystem boundary',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Sandbox guards',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Boundary enforced; not an approved model.',
    codeEvidenceSummary: 'dev_web_safety_baseline.py + dev_web_sandbox_guards.py.',
    humanReviewRequirement: 'Approved filesystem-boundary model.',
    reviewerCategory: 'security reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'enable runtime'],
    sourcePhase: 'Phase 3E-H safety baseline',
    relatedArtifacts: ['dev_web_safety_baseline.py', 'dev_web_sandbox_guards.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-04',
    title: 'Network boundary',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Sandbox guards',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Intent-level deny only; no approved network policy.',
    codeEvidenceSummary: 'dev_web_sandbox_guards.py network deny.',
    humanReviewRequirement: 'Approved network-boundary model.',
    reviewerCategory: 'security reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'enable runtime'],
    sourcePhase: 'Phase 3H proof runner',
    relatedArtifacts: ['dev_web_sandbox_guards.py', 'test_dev_web_phase_3h_sandbox_proof_skeleton.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-05',
    title: 'Supply-chain policy',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Sandbox guards',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Provenance classifier denies untrusted sources; no approved policy.',
    codeEvidenceSummary: 'dev_web_sandbox_guards.py + classify_plugin_source.',
    humanReviewRequirement: 'Approved supply-chain policy plus supply-chain trust proof.',
    reviewerCategory: 'security reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'remote registry', 'marketplace'],
    sourcePhase: 'Phase 3E-H safety baseline',
    relatedArtifacts: ['dev_web_sandbox_guards.py', 'dev_web_p0_evidence.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-06',
    title: 'Permission model',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Sandbox guards',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Labels grant nothing at runtime; no real permission model.',
    codeEvidenceSummary: 'dev_web_sandbox_policy.py capability default-deny.',
    humanReviewRequirement: 'Approved permission model.',
    reviewerCategory: 'capability reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'enable runtime'],
    sourcePhase: 'Phase 3H proof runner',
    relatedArtifacts: ['dev_web_sandbox_policy.py', 'test_dev_web_phase_3h_sandbox_proof_skeleton.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-07',
    title: 'Audit / redaction model',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Audit redaction',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'In-memory only; no durable audit approved.',
    codeEvidenceSummary: 'dev_web_sandbox_audit.py + dev_web_sandbox_guards.py redaction.',
    humanReviewRequirement: 'Approved audit / redaction model.',
    reviewerCategory: 'audit reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'audit store write'],
    sourcePhase: 'Phase 3H proof runner',
    relatedArtifacts: ['dev_web_sandbox_audit.py', 'dev_web_sandbox_guards.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-08',
    title: 'Kill switch',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Production safety',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Dev-only flag; not a production kill switch.',
    codeEvidenceSummary: 'dev_web_sandbox_policy.py evaluate_kill_switch.',
    humanReviewRequirement: 'Approved kill switch.',
    reviewerCategory: 'production safety reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'production rollout'],
    sourcePhase: 'Phase 3H proof runner',
    relatedArtifacts: ['dev_web_sandbox_policy.py', 'test_dev_web_phase_3h_sandbox_proof_skeleton.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-09',
    title: 'Production isolation',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Production safety',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Production referenced only as denial target; not an approved boundary.',
    codeEvidenceSummary: 'dev_web_safety_baseline.py string-only denial.',
    humanReviewRequirement: 'Approved production-isolation model.',
    reviewerCategory: 'production safety reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'production rollout'],
    sourcePhase: 'Phase 3E-H safety baseline',
    relatedArtifacts: ['dev_web_safety_baseline.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-10',
    title: 'Secret handling ambiguity',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Audit redaction',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Redaction is defense-in-depth; no approved secret model; no real secret read.',
    codeEvidenceSummary: 'dev_web_sandbox_guards.py redaction.',
    humanReviewRequirement: 'Unambiguous secret handling.',
    reviewerCategory: 'security reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'API key entry', 'real secret read'],
    sourcePhase: 'Phase 3H proof runner',
    relatedArtifacts: ['dev_web_sandbox_guards.py', 'test_dev_web_phase_3h_sandbox_proof_skeleton.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-11',
    title: 'Filesystem / network ambiguity',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Sandbox guards',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Pure deterministic evaluators; not approved by reviewers.',
    codeEvidenceSummary: 'dev_web_safety_baseline.py + dev_web_sandbox_guards.py.',
    humanReviewRequirement: 'Unambiguous filesystem / network access.',
    reviewerCategory: 'security reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'external network'],
    sourcePhase: 'Phase 3E-H safety baseline',
    relatedArtifacts: ['dev_web_safety_baseline.py', 'dev_web_sandbox_guards.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-12',
    title: 'Unapproved execution path',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Sandbox guards',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Proven absent; remains not-introduced.',
    codeEvidenceSummary: 'dev_web_sandbox_policy.py descriptor-only execution.',
    humanReviewRequirement: 'No unapproved execution path.',
    reviewerCategory: 'security reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'run plugin', 'batch execute'],
    sourcePhase: 'Phase 3H proof runner',
    relatedArtifacts: ['dev_web_sandbox_policy.py', 'test_dev_web_phase_3h_sandbox_proof_skeleton.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-13',
    title: 'Production impact',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Production safety',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'None introduced.',
    codeEvidenceSummary: 'dev_web_safety_baseline.py string-only.',
    humanReviewRequirement: 'No production impact.',
    reviewerCategory: 'production safety reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'production rollout'],
    sourcePhase: 'Phase 3E-H safety baseline',
    relatedArtifacts: ['dev_web_safety_baseline.py', 'test_dev_web_phase_3e_h_safety_baseline.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-14',
    title: 'Route governance',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Route governance',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Baseline frozen unchanged; no exception approval granted.',
    codeEvidenceSummary: 'dev_web_safety_baseline.py 34/34/5/0/1/1.',
    humanReviewRequirement: 'Route-governance approval for any new route.',
    reviewerCategory: 'route-governance reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'new backend route'],
    sourcePhase: 'Phase 3E-H safety baseline',
    relatedArtifacts: ['dev_web_safety_baseline.py', 'test_dev_web_phase_3e_h_safety_baseline.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-15',
    title: 'No implementation authorization',
    status: 'blocked_by_human_review',
    statusLabel: 'Pending human review',
    category: 'Human approval',
    evidenceLevel: 'human_review_required',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason:
      'Requires project-owner authorization; cannot be granted by code or metadata.',
    codeEvidenceSummary: 'Proof authorization cannot be automated.',
    humanReviewRequirement: 'Explicit implementation authorization after gates clear.',
    reviewerCategory: 'project owner',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'authorize', 'signoff', 'resolve', 'override'],
    sourcePhase: 'Phase 3E-H safety baseline',
    relatedArtifacts: ['dev_web_p0_evidence.py', 'test_dev_web_phase_3e_h_remaining_p0_reduction.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-16',
    title: 'No runtime endpoint authorization',
    status: 'blocked_by_human_review',
    statusLabel: 'Pending human review',
    category: 'Route governance',
    evidenceLevel: 'human_review_required',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason:
      'No runtime endpoint wired; endpoint authorization requires route-governance reviewer.',
    codeEvidenceSummary: 'dev_web_p0_evidence.py route exception evaluator.',
    humanReviewRequirement: 'Explicit runtime endpoint authorization.',
    reviewerCategory: 'route-governance reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'authorize', 'signoff', 'resolve', 'override', 'new backend route'],
    sourcePhase: 'Phase 3E-H safety baseline',
    relatedArtifacts: ['dev_web_p0_evidence.py', 'test_dev_web_phase_3e_h_remaining_p0_reduction.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-17',
    title: 'No runtime artifact storage authorization',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Audit redaction',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'No persistent artifact store exists; approved storage model still required.',
    codeEvidenceSummary: 'dev_web_sandbox_audit.py in-memory only.',
    humanReviewRequirement: 'Approved runtime artifact storage model.',
    reviewerCategory: 'audit reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'audit store write'],
    sourcePhase: 'Phase 3H proof runner',
    relatedArtifacts: ['dev_web_sandbox_audit.py', 'test_dev_web_phase_3h_sandbox_proof_skeleton.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-18',
    title: 'No plugin source trust decision',
    status: 'blocked_by_human_review',
    statusLabel: 'Pending human review',
    category: 'Descriptor registry',
    evidenceLevel: 'human_review_required',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason:
      'Deny-by-default provenance; an explicit trust decision requires security reviewer.',
    codeEvidenceSummary: 'dev_web_p0_evidence.py classify_plugin_source deny-by-default.',
    humanReviewRequirement: 'Explicit plugin source trust decision.',
    reviewerCategory: 'security reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: [
      'approve',
      'authorize',
      'signoff',
      'resolve',
      'override',
      'arbitrary plugin loading',
      'remote registry',
      'marketplace',
    ],
    sourcePhase: 'Phase 3E-H safety baseline',
    relatedArtifacts: ['dev_web_p0_evidence.py', 'test_dev_web_phase_3e_h_remaining_p0_reduction.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-19',
    title: 'No worker lifecycle approval',
    status: 'blocked_by_human_review',
    statusLabel: 'Pending human review',
    category: 'Runtime isolation',
    evidenceLevel: 'human_review_required',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'No worker lifecycle code; approval requires security reviewer.',
    codeEvidenceSummary: 'dev_web_sandbox_policy.py process.spawn denied.',
    humanReviewRequirement: 'Approved worker lifecycle.',
    reviewerCategory: 'security reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'authorize', 'signoff', 'resolve', 'override', 'enable runtime'],
    sourcePhase: 'Phase 3H proof runner',
    relatedArtifacts: ['dev_web_sandbox_policy.py', 'test_dev_web_phase_3h_sandbox_proof_skeleton.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-20',
    title: 'No failure-mode approval',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Production safety',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Fail-closed defaults implemented; not an approved failure-mode plan.',
    codeEvidenceSummary: 'dev_web_sandbox_policy.py + dev_web_sandbox_audit.py fail-closed.',
    humanReviewRequirement: 'Approved failure-mode behavior.',
    reviewerCategory: 'security reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'production rollout'],
    sourcePhase: 'Phase 3H proof runner',
    relatedArtifacts: ['dev_web_sandbox_policy.py', 'dev_web_sandbox_audit.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-21',
    title: 'No rollback plan',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Rollback / readiness',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Rollback readiness evaluator uses temp/fake targets only; approved plan required.',
    codeEvidenceSummary: 'dev_web_p0_evidence.py evaluate_rollback_readiness.',
    humanReviewRequirement: 'Approved rollback / incident-response plan for implementation.',
    reviewerCategory: 'production safety reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'production rollout'],
    sourcePhase: 'Phase 3E-H safety baseline',
    relatedArtifacts: ['dev_web_p0_evidence.py', 'test_dev_web_phase_3e_h_remaining_p0_reduction.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-22',
    title: 'No human review signoff',
    status: 'blocked_by_human_review',
    statusLabel: 'Pending human review',
    category: 'Human approval',
    evidenceLevel: 'human_review_required',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Signoff not started; cannot be synthesized from metadata.',
    codeEvidenceSummary: 'dev_web_p0_evidence.py HumanApprovalRecord cannot be faked.',
    humanReviewRequirement: 'Human review signoff for implementation.',
    reviewerCategory: 'project owner',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'authorize', 'signoff', 'resolve', 'override', 'mark approved'],
    sourcePhase: 'Phase 3E-H safety baseline',
    relatedArtifacts: ['dev_web_p0_evidence.py', 'test_dev_web_phase_3e_h_remaining_p0_reduction.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-23',
    title: 'No incident response plan',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Rollback / readiness',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Incident owner/redaction helper added; approved plan required.',
    codeEvidenceSummary: 'dev_web_p0_evidence.py incident owner + redaction.',
    humanReviewRequirement: 'Approved incident-response plan.',
    reviewerCategory: 'production safety reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override', 'production rollout'],
    sourcePhase: 'Phase 3E-H safety baseline',
    relatedArtifacts: ['dev_web_p0_evidence.py', 'test_dev_web_phase_3e_h_remaining_p0_reduction.py'],
    productionAuthorizationImpact: 'NO-GO',
  },
  {
    gateId: 'P0-24',
    title: 'No test strategy approval',
    status: 'partial_evidence',
    statusLabel: 'Partial evidence',
    category: 'Evidence reproducibility',
    evidenceLevel: 'partial_code_evidence',
    requiresHumanReview: true,
    resolved: false,
    approved: false,
    blockedReason: 'Test strategy not approved by reviewers.',
    codeEvidenceSummary: 'tests/test_dev_web_phase_3e_h_*.py suite.',
    humanReviewRequirement: 'Approved test strategy.',
    reviewerCategory: 'implementation owner + security reviewer',
    allowedNextAction: 'await_out_of_band_human_review',
    forbiddenActions: ['approve', 'resolve', 'override'],
    sourcePhase: 'Phase 3E-H safety baseline',
    relatedArtifacts: [
      'test_dev_web_phase_3e_h_safety_baseline.py',
      'test_dev_web_phase_3h_sandbox_proof_skeleton.py',
      'test_dev_web_phase_3e_h_p0_evidence_hardening.py',
    ],
    productionAuthorizationImpact: 'NO-GO',
  },
])

/** The frozen conservative summary over the 24-gate registry. */
export const HUMAN_REVIEW_SUMMARY: HumanReviewSummary = deepFreeze({
  totalGates: 24,
  resolvedCount: 0,
  partialEvidenceCount: 19,
  pendingHumanReviewCount: 5,
  candidateForReviewCount: 0,
  governanceOnlyCount: 0,
  noEvidenceCount: 0,
  unresolvedCount: 24,
  implementationAuthorization: 'NO-GO',
  phase3iProductionAuthorization: 'NOT_AUTHORIZED',
  productionRuntimeAuthorization: 'NO-GO',
  newRouteAuthorization: 'NO-GO',
  productionRolloutAuthorization: 'NO-GO',
  trustTokenProvisioned: false,
  classificationNote:
    'Code and test evidence is partial evidence only. It never resolves a P0 ' +
    'gate, never authorizes production, never provisions a trust token, and ' +
    'never authorizes a real runtime. The 5 pending-human-review gates can ' +
    'only advance via a valid out-of-band human approval the dev skeleton ' +
    'cannot produce — fake metadata, AI approval, or placeholder approval ' +
    'cannot resolve them.',
})

/**
 * The frozen evidence trail across the Phase 3 capability chain (mirrors the
 * phases that produced the partial evidence). Each source states what it proves
 * and — explicitly — what it does NOT prove. None of these authorizes
 * production.
 */
export const HUMAN_REVIEW_EVIDENCE_TRAIL: readonly HumanReviewEvidenceSource[] = deepFreeze([
  {
    phase: 'Phase 3E-H safety baseline',
    evidenceType: 'Static safety / route-governance baseline',
    whatItProves:
      'Deterministic string-only evaluators enforce the filesystem, network, ' +
      'production-isolation, and route-governance (34/34/5/0/1/1) boundaries.',
    whatItDoesNotProve:
      'It is a baseline, not an approved model. It authorizes no production ' +
      'runtime and grants no route exception.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
  {
    phase: 'Phase 3H proof runner',
    evidenceType: 'Dev-only sandbox proof skeleton + adversarial tests',
    whatItProves:
      'A fail-closed, in-process skeleton proves process.spawn is denied, the ' +
      'network is intent-level denied, secrets are redacted, and no unapproved ' +
      'execution path exists.',
    whatItDoesNotProve:
      'The skeleton is not an approved runtime sandbox, worker lifecycle, or ' +
      'failure-mode plan. It runs no real plugin and reads no real secret.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
  {
    phase: 'Phase 3I local runtime MVP',
    evidenceType: 'Dev-only descriptor-backed fixture runtime',
    whatItProves:
      'A reviewed-fixture descriptor registry can bind to an in-process fixture ' +
      'allowlist and run fail-closed without side effects.',
    whatItDoesNotProve:
      'Fixture execution is dev-only partial evidence. It never loads a real ' +
      'plugin, never reads from disk, and never reaches production.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
  {
    phase: 'Phase 3I runtime expansion',
    evidenceType: 'Multi-descriptor batch + redacted audit projection',
    whatItProves:
      'A batch can run isolated and fail-closed, and a redacted audit can be ' +
      'projected from a run / batch report without re-execution.',
    whatItDoesNotProve:
      'The audit is in-memory only; no durable artifact store is approved, and ' +
      'no runtime endpoint is wired.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
  {
    phase: 'Phase 3I descriptor runtime integration',
    evidenceType: 'Registry-to-runtime binding integration',
    whatItProves:
      'A reviewed descriptor resolves to a fixture binding through the static ' +
      'descriptor registry with deny-by-default provenance.',
    whatItDoesNotProve:
      'No plugin source trust decision is granted; arbitrary / remote / ' +
      'marketplace sources remain denied.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
  {
    phase: 'Phase 3I runtime governance CLI',
    evidenceType: 'Read-only governance report projections',
    whatItProves:
      'A CLI can project the frozen no-side-effect surface and the all-NO-GO ' +
      'authorization verdicts without executing anything.',
    whatItDoesNotProve:
      'A governance pass authorizes nothing. It cannot approve a gate, cannot ' +
      'sign off, and cannot provision a trust token.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
  {
    phase: 'Phase 3J read-only WebUI',
    evidenceType: 'Read-only runtime governance WebUI surface',
    whatItProves:
      'The WebUI can render the descriptor registry, binding detail, P0 summary, ' +
      'and CLI examples read-only with no execution and no new route.',
    whatItDoesNotProve:
      'The WebUI is read-only evidence. It executes no runtime, loads no plugin, ' +
      'and adds no backend route.',
    authorizationImpact: 'Partial evidence only — no production authorization',
  },
])

/** The frozen NO-GO decision block. Every dimension is frozen NO-GO / not-authorized. */
export const HUMAN_REVIEW_NOGO_DECISIONS: readonly HumanReviewNogoDecision[] = deepFreeze([
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
    key: 'newRouteAuthorization',
    label: 'New Backend Route',
    verdict: 'NO-GO',
    reason: 'Route baseline frozen at 34/34/5/0/1/1; P0-16 endpoint authorization is pending.',
  },
  {
    key: 'productionRolloutAuthorization',
    label: 'Production Rollout',
    verdict: 'NO-GO',
    reason: 'No approved rollback / incident plan; no trust token provisioned; production access forbidden.',
  },
])

/**
 * The frozen relationship between Runtime Governance and Human Review. Neither
 * surface can approve production, execute a production runtime, or change route
 * governance.
 */
export const HUMAN_REVIEW_RUNTIME_RELATIONSHIP: readonly HumanReviewRelationshipItem[] = deepFreeze([
  {
    key: 'runtimeGovernanceRole',
    label: 'Runtime Governance (CLI / WebUI)',
    detail: 'An EVIDENCE surface — it projects what code can prove read-only.',
  },
  {
    key: 'humanReviewRole',
    label: 'Human Review Governance',
    detail: 'A DECISION-READINESS surface — it projects what only human review can approve.',
  },
  {
    key: 'neitherApproves',
    label: 'Neither approves production',
    detail: 'Neither surface can approve a gate, authorize a runtime, or sign off.',
  },
  {
    key: 'neitherExecutes',
    label: 'Neither executes a production runtime',
    detail: 'Neither surface runs a real plugin, reads a real secret, or reaches production.',
  },
  {
    key: 'neitherChangesRoutes',
    label: 'Neither changes route governance',
    detail: 'Neither surface adds a backend route or grants a route exception.',
  },
])

/**
 * Global actions the WebUI must NOT offer. Rendered as forbidden explanatory
 * TEXT only — never as an interactive control.
 */
export const HUMAN_REVIEW_FORBIDDEN_ACTIONS: readonly string[] = deepFreeze([
  'approve',
  'reject',
  'authorize',
  'signoff',
  'resolve',
  'override',
  'production rollout',
  'enable production runtime',
  'arbitrary plugin loading',
  'local plugin directory loading',
  'remote registry',
  'marketplace',
  'API key entry',
  'external network',
  'run plugin from WebUI',
  'batch execute from WebUI',
  'upload evidence',
])

/**
 * Global UI actions the read-only surface MAY offer. Every one is a harmless
 * client-only affordance that operates on static data — none calls the backend,
 * the runtime, or the CLI.
 */
export const HUMAN_REVIEW_ALLOWED_UI_ACTIONS: readonly string[] = deepFreeze([
  'view gate details',
  'filter gates',
  'inspect evidence summary',
  'copy gate id',
  'read NO-GO explanation',
])

/** Frozen page-header status badges (explicit non-color text). */
export const HUMAN_REVIEW_STATUS_BADGES: readonly HumanReviewStatusBadge[] = deepFreeze([
  { label: 'READ-ONLY' },
  { label: 'P0 GATES' },
  { label: 'HUMAN REVIEW REQUIRED' },
  { label: 'NO APPROVAL FROM WEBUI' },
  { label: 'PRODUCTION NO-GO' },
])

/** Frozen boundary-banner rows (icon kind + explicit non-color text). */
export const HUMAN_REVIEW_BOUNDARY_ITEMS: readonly HumanReviewBoundaryItem[] = deepFreeze([
  { kind: 'lock', label: 'READ-ONLY — this page cannot approve gates' },
  { kind: 'lock', label: 'READ-ONLY — this page cannot authorize runtime' },
  { kind: 'lock', label: 'READ-ONLY — this page cannot resolve P0' },
  { kind: 'lock', label: 'READ-ONLY — this page cannot enable production' },
  { kind: 'lock', label: 'READ-ONLY — this page cannot replace human review' },
  { kind: 'ban', label: 'Code evidence is partial evidence only' },
  { kind: 'ban', label: 'Valid approval requires an out-of-band trusted human process' },
  { kind: 'ban', label: 'Fake / AI / placeholder approval cannot resolve P0' },
  { kind: 'ban', label: 'Metadata cannot approve gates' },
  { kind: 'ban', label: 'NO trust token provisioned' },
  { kind: 'ban', label: 'NO production rollout' },
  { kind: 'ban', label: 'NO new backend route — route counts unchanged' },
])
