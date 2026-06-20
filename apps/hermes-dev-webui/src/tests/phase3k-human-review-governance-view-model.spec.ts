/**
 * Phase 3K — Human Review Governance view-model tests.
 *
 * Asserts the pure view-model projections are deterministic, carry the 24 frozen
 * gates (19 partial evidence, 5 pending human review, 0 resolved), the frozen
 * NO-GO / not-authorized summary and decisions, the evidence trail, the
 * runtime-relationship rows, the client-side filters, immutability (an external
 * mutation cannot reach the canonical manifest), and that the defense-in-depth
 * redactor masks every secret-shaped / production-path-shaped /
 * fake-approval-shaped substring (redaction corpus M).
 */
import { describe, it, expect } from 'vitest'

import {
  buildHumanReviewViewModel,
  buildHumanReviewGates,
  buildHumanReviewSummary,
  buildHumanReviewSummaryCards,
  buildHumanReviewEvidenceTrail,
  buildHumanReviewNogoDecisions,
  buildHumanReviewRuntimeRelationship,
  buildHumanReviewForbiddenActions,
  buildHumanReviewAllowedUiActions,
  buildHumanReviewStatusBadges,
  buildHumanReviewBoundaryItems,
  findHumanReviewGate,
  filterHumanReviewGates,
  redactHumanReviewValue,
  sanitizeHumanReviewDisplayText,
  everyGateUnresolved,
  everyNogoDecisionHolds,
  DEFAULT_GATE_ID,
  HUMAN_REVIEW_FILTER_OPTIONS,
} from '@/lib/humanReviewGovernanceViewModel'
import {
  HUMAN_REVIEW_GATES,
  HUMAN_REVIEW_SUMMARY,
  HUMAN_REVIEW_EVIDENCE_TRAIL,
  HUMAN_REVIEW_NOGO_DECISIONS,
  HUMAN_REVIEW_FORBIDDEN_ACTIONS,
} from '@/constants/humanReviewGovernanceManifest'

const PARTIAL_GATE_IDS = [
  'P0-01',
  'P0-02',
  'P0-03',
  'P0-04',
  'P0-05',
  'P0-06',
  'P0-07',
  'P0-08',
  'P0-09',
  'P0-10',
  'P0-11',
  'P0-12',
  'P0-13',
  'P0-14',
  'P0-17',
  'P0-20',
  'P0-21',
  'P0-23',
  'P0-24',
]
const PENDING_GATE_IDS = ['P0-15', 'P0-16', 'P0-18', 'P0-19', 'P0-22']

describe('humanReviewGovernanceViewModel (Phase 3K) — determinism + counts', () => {
  it('is deterministic — two builds are deeply equal', () => {
    const a = buildHumanReviewViewModel()
    const b = buildHumanReviewViewModel()
    expect(JSON.stringify(a)).toEqual(JSON.stringify(b))
  })

  it('projects exactly 24 gates (19 partial + 5 pending, 0 resolved)', () => {
    const vm = buildHumanReviewViewModel()
    expect(vm.gateCount).toBe(24)
    expect(vm.gates).toHaveLength(24)
    const partial = vm.gates.filter((g) => g.status === 'partial_evidence')
    const pending = vm.gates.filter((g) => g.status === 'blocked_by_human_review')
    expect(partial).toHaveLength(19)
    expect(pending).toHaveLength(5)
    expect(partial.map((g) => g.gateId).sort()).toEqual([...PARTIAL_GATE_IDS].sort())
    expect(pending.map((g) => g.gateId).sort()).toEqual([...PENDING_GATE_IDS].sort())
  })

  it('the frozen summary projects 24 / 0 / 19 / 5 and every authorization NO-GO', () => {
    const s = buildHumanReviewSummary()
    expect(s.totalGates).toBe(24)
    expect(s.resolvedCount).toBe(0)
    expect(s.partialEvidenceCount).toBe(19)
    expect(s.pendingHumanReviewCount).toBe(5)
    expect(s.candidateForReviewCount).toBe(0)
    expect(s.governanceOnlyCount).toBe(0)
    expect(s.noEvidenceCount).toBe(0)
    expect(s.unresolvedCount).toBe(24)
    expect(s.implementationAuthorization).toBe('NO-GO')
    expect(s.phase3iProductionAuthorization).toBe('NOT_AUTHORIZED')
    expect(s.productionRuntimeAuthorization).toBe('NO-GO')
    expect(s.newRouteAuthorization).toBe('NO-GO')
    expect(s.productionRolloutAuthorization).toBe('NO-GO')
    expect(s.trustTokenProvisioned).toBe(false)
  })

  it('every gate is unresolved / not approved / production NO-GO', () => {
    const gates = buildHumanReviewGates()
    expect(everyGateUnresolved(gates)).toBe(true)
    for (const g of gates) {
      expect(g.resolved).toBe(false)
      expect(g.approved).toBe(false)
      expect(g.requiresHumanReview).toBe(true)
      expect(g.productionAuthorizationImpact).toBe('NO-GO')
      expect(g.allowedNextAction).toBe('await_out_of_band_human_review')
    }
  })

  it('every NO-GO decision holds NO-GO / NOT_AUTHORIZED', () => {
    const decisions = buildHumanReviewNogoDecisions()
    expect(everyNogoDecisionHolds(decisions)).toBe(true)
    const keys = decisions.map((d) => d.key)
    expect(keys).toContain('implementationAuthorization')
    expect(keys).toContain('phase3iProductionAuthorization')
    expect(keys).toContain('productionRuntimeAuthorization')
    expect(keys).toContain('newRouteAuthorization')
    expect(keys).toContain('productionRolloutAuthorization')
  })
})

describe('humanReviewGovernanceViewModel — gate lookup + filters', () => {
  it('findHumanReviewGate returns the gate by id and undefined for unknown ids', () => {
    expect(findHumanReviewGate('P0-15')?.title).toBe('No implementation authorization')
    expect(findHumanReviewGate('P0-22')?.title).toBe('No human review signoff')
    expect(findHumanReviewGate('P0-99')).toBeUndefined()
    expect(findHumanReviewGate(null)).toBeUndefined()
  })

  it('the default gate id is a pending-human-review gate', () => {
    expect(DEFAULT_GATE_ID).toBe('P0-15')
    expect(findHumanReviewGate(DEFAULT_GATE_ID)?.status).toBe('blocked_by_human_review')
  })

  it('the All filter returns 24 gates', () => {
    expect(filterHumanReviewGates('all')).toHaveLength(24)
  })

  it('the Partial evidence filter returns 19 gates', () => {
    expect(filterHumanReviewGates('partial_evidence')).toHaveLength(19)
  })

  it('the Pending human review filter returns 5 gates', () => {
    expect(filterHumanReviewGates('pending_human_review')).toHaveLength(5)
  })

  it('the Blocked by human review filter returns the same 5 gates', () => {
    const blocked = filterHumanReviewGates('blocked_by_human_review')
    expect(blocked).toHaveLength(5)
    expect(blocked.map((g) => g.gateId).sort()).toEqual([...PENDING_GATE_IDS].sort())
  })

  it('the Governance-only filter returns 0 gates', () => {
    expect(filterHumanReviewGates('governance_only')).toHaveLength(0)
  })

  it('exposes exactly five filter options', () => {
    expect(HUMAN_REVIEW_FILTER_OPTIONS.map((o) => o.key)).toEqual([
      'all',
      'partial_evidence',
      'pending_human_review',
      'blocked_by_human_review',
      'governance_only',
    ])
  })
})

describe('humanReviewGovernanceViewModel — evidence trail + relationship + actions', () => {
  it('projects the seven evidence-trail sources, each with prove / does-not-prove / partial impact', () => {
    const trail = buildHumanReviewEvidenceTrail()
    expect(trail).toHaveLength(7)
    const phases = trail.map((s) => s.phase)
    expect(phases).toContain('Phase 3E-H safety baseline')
    expect(phases).toContain('Phase 3H proof runner')
    expect(phases).toContain('Phase 3I local runtime MVP')
    expect(phases).toContain('Phase 3I runtime governance CLI')
    expect(phases).toContain('Phase 3J read-only WebUI')
    for (const s of trail) {
      expect(s.whatItProves.trim().length).toBeGreaterThan(0)
      expect(s.whatItDoesNotProve.trim().length).toBeGreaterThan(0)
      expect(s.authorizationImpact).toBe('Partial evidence only — no production authorization')
    }
  })

  it('projects the runtime-relationship rows', () => {
    const rel = buildHumanReviewRuntimeRelationship()
    expect(rel.length).toBeGreaterThanOrEqual(5)
    const details = rel.map((r) => r.detail)
    expect(details.some((d) => /evidence surface/i.test(d))).toBe(true)
    expect(details.some((d) => /decision-readiness surface/i.test(d))).toBe(true)
  })

  it('forbidden actions include approve / authorize / production rollout and cannot be drained', () => {
    const actions = buildHumanReviewForbiddenActions()
    const joined = actions.join(' ')
    expect(joined).toContain('approve')
    expect(joined).toContain('authorize')
    expect(joined).toContain('production rollout')
    expect(joined).toContain('arbitrary plugin loading')
    expect(joined).toContain('remote registry')
    expect(joined).toContain('marketplace')
  })

  it('allowed UI actions are read-only affordances only', () => {
    const actions = buildHumanReviewAllowedUiActions()
    const joined = actions.join(' ')
    expect(joined).toContain('view gate details')
    expect(joined).toContain('filter gates')
    expect(joined).toContain('copy gate id')
  })

  it('summary cards include the eight required counts/verdicts', () => {
    const cards = buildHumanReviewSummaryCards()
    const byLabel = new Map(cards.map((c) => [c.label, c]))
    expect(byLabel.get('Total P0 gates')!.value).toBe(24)
    expect(byLabel.get('Resolved')!.value).toBe(0)
    expect(byLabel.get('Partial evidence')!.value).toBe(19)
    expect(byLabel.get('Pending human review')!.value).toBe(5)
    expect(byLabel.get('Governance-only')!.value).toBe(0)
    expect(byLabel.get('Implementation Authorization')!.value).toBe('NO-GO')
    expect(byLabel.get('Production runtime')!.value).toBe('NO-GO')
    expect(byLabel.get('Production rollout')!.value).toBe('NO-GO')
    expect(byLabel.get('Backend routes changed')!.value).toBe('no')
  })

  it('status badges and boundary items project frozen, labelled rows', () => {
    expect(buildHumanReviewStatusBadges().map((b) => b.label)).toEqual([
      'READ-ONLY',
      'P0 GATES',
      'HUMAN REVIEW REQUIRED',
      'NO APPROVAL FROM WEBUI',
      'PRODUCTION NO-GO',
    ])
    const items = buildHumanReviewBoundaryItems()
    expect(items.length).toBeGreaterThan(0)
    for (const it of items) {
      expect(it.kind === 'lock' || it.kind === 'ban' || it.kind === 'user').toBe(true)
      expect(it.label.trim().length).toBeGreaterThan(0)
    }
  })

  it('route governance baseline + backend-routes-unchanged flag', () => {
    const vm = buildHumanReviewViewModel()
    expect(vm.routeGovernanceBaseline).toBe('34/34/5/0/1/1')
    expect(vm.backendRoutesChanged).toBe(false)
    expect(vm.schemaVersion).toBe('phase-3k-human-review-governance-v1')
  })
})

describe('humanReviewGovernanceViewModel — immutability', () => {
  it('the canonical manifest exports are frozen', () => {
    expect(Object.isFrozen(HUMAN_REVIEW_GATES)).toBe(true)
    expect(Object.isFrozen(HUMAN_REVIEW_GATES[0])).toBe(true)
    expect(Object.isFrozen(HUMAN_REVIEW_SUMMARY)).toBe(true)
    expect(Object.isFrozen(HUMAN_REVIEW_EVIDENCE_TRAIL)).toBe(true)
    expect(Object.isFrozen(HUMAN_REVIEW_NOGO_DECISIONS)).toBe(true)
    expect(Object.isFrozen(HUMAN_REVIEW_FORBIDDEN_ACTIONS)).toBe(true)
  })

  it('mutating a returned gate does not mutate the canonical manifest', () => {
    const before = HUMAN_REVIEW_GATES[0]!.title
    const gates = buildHumanReviewGates()
    gates[0]!.title = 'tampered'
    expect(gates[0]!.title).toBe('tampered') // local copy is independently mutable
    expect(HUMAN_REVIEW_GATES[0]!.title).toBe(before) // canonical untouched
  })

  it('mutating a returned forbiddenActions list does not drain the canonical list', () => {
    const actions = buildHumanReviewForbiddenActions()
    actions.push('approve')
    actions.length = 0
    expect(HUMAN_REVIEW_FORBIDDEN_ACTIONS.length).toBeGreaterThan(0)
    expect(buildHumanReviewForbiddenActions().includes('approve')).toBe(true)
  })

  it('mutating a returned summary cannot flip resolved / NO-GO values', () => {
    const s = buildHumanReviewSummary()
    s.resolvedCount = 24 as unknown as 0
    s.implementationAuthorization = 'GO' as unknown as 'NO-GO'
    // Fresh build is still the frozen conservative state.
    const fresh = buildHumanReviewSummary()
    expect(fresh.resolvedCount).toBe(0)
    expect(fresh.implementationAuthorization).toBe('NO-GO')
  })

  it('mutating a returned evidence trail does not mutate the canonical trail', () => {
    const trail = buildHumanReviewEvidenceTrail()
    trail[0]!.whatItProves = 'tampered'
    expect(HUMAN_REVIEW_EVIDENCE_TRAIL[0]!.whatItProves).not.toBe('tampered')
    expect(buildHumanReviewEvidenceTrail()[0]!.whatItProves).not.toBe('tampered')
  })
})

describe('defense-in-depth redactor (corpus M)', () => {
  const CORPUS = [
    'sk-FAKE-SECRET-DO-NOT-LEAK-12345678',
    'Authorization: Bearer fake-token',
    'ghp_fakegithubtoken',
    'xox-fake-slack-token',
    '-----BEGIN PRIVATE KEY-----',
    'BEGIN PRIVATE KEY fake',
    'OPENAI_API_KEY=fake',
    'db_password=fake',
    'accessToken=fake',
    '~/.hermes',
    '/fake/production/state.db',
    'implementation_authorization=GO',
    'phase_3i_authorized=true',
    'production_approved=true',
    'route_exception_approved=true',
    'approved_by_ai=true',
    'trust_token=fake',
  ]

  it.each(CORPUS)('masks secret-shaped / fake-approval value %s', (value) => {
    expect(redactHumanReviewValue(value)).toBe('[REDACTED]')
  })

  it('sanitizeHumanReviewDisplayText is a stable alias of redactHumanReviewValue', () => {
    for (const c of CORPUS) {
      expect(sanitizeHumanReviewDisplayText(c)).toBe('[REDACTED]')
    }
  })

  it('leaves safe governance text intact', () => {
    expect(redactHumanReviewValue('No implementation authorization')).toContain('authorization')
    expect(redactHumanReviewValue('Phase 3I runtime governance CLI')).toContain('governance')
  })

  it('the static manifest carries no secret-shaped gate text', () => {
    for (const g of HUMAN_REVIEW_GATES) {
      const texts = [
        g.title,
        g.blockedReason,
        g.codeEvidenceSummary,
        g.humanReviewRequirement,
        ...g.relatedArtifacts,
      ]
      for (const text of texts) {
        for (const c of CORPUS) {
          expect(text).not.toContain(c)
        }
      }
    }
  })
})
