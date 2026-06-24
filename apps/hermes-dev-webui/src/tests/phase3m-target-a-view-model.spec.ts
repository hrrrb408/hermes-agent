/**
 * Phase 3M — Target A Completion view-model tests.
 *
 * Asserts the pure Target A projections are deterministic, carry the frozen
 * summary (24 / 0 / 19 / 5, every authorization NO-GO, production readiness
 * NO-GO), the 15-row capability matrix, the 15-item readiness checklist (every
 * item pass), the 28-row Target B deferred matrix (every row NO-GO), the release
 * readiness block, immutability (an external mutation cannot reach the canonical
 * manifest, cannot flip a NO-GO, cannot raise P0 resolved above 0, cannot
 * authorize Target B), and that the defense-in-depth redactor masks every
 * secret-shaped / production-path-shaped / fake-approval-shaped substring —
 * including the Target-B fake-authorization markers.
 */
import { describe, it, expect } from 'vitest'

import {
  buildGovernanceHubViewModel,
  buildTargetACompletionViewModel,
  buildTargetACompletionSummary,
  buildTargetACompletionCards,
  buildTargetACapabilityMatrix,
  buildTargetAReadinessChecklist,
  buildTargetBDeferredMatrix,
  buildTargetASummaryText,
  redactGovernanceHubValue,
} from '@/lib/governanceHubViewModel'
import {
  TARGET_A_COMPLETION_SUMMARY,
  TARGET_A_CAPABILITY_MATRIX,
  TARGET_A_READINESS_CHECKLIST,
  TARGET_B_DEFERRED_MATRIX,
  TARGET_A_ACCEPTANCE,
  TARGET_A_RELEASE_READINESS,
} from '@/constants/governanceHubManifest'

describe('targetACompletion view-model (Phase 3M) — determinism + summary', () => {
  it('is deterministic — two builds are deeply equal', () => {
    const a = buildTargetACompletionViewModel()
    const b = buildTargetACompletionViewModel()
    expect(JSON.stringify(a)).toEqual(JSON.stringify(b))
  })

  it('the frozen summary is COMPLETE dev-only with production readiness NO-GO', () => {
    const s = buildTargetACompletionSummary()
    expect(s.targetName).toBe('Dev-only Runtime Prototype')
    expect(s.targetStatus).toBe('COMPLETE')
    expect(s.targetScope).toBe('dev-only / fixture-only / read-only governed')
    expect(s.completionLabel).toBe('Dev-only runtime prototype complete')
    expect(s.completionPercentage).toBe(100)
    expect(s.productionReadiness).toBe('NO-GO')
    expect(s.notProduction).toBe(true)
    expect(s.p0Total).toBe(24)
    expect(s.p0Resolved).toBe(0)
    expect(s.p0Partial).toBe(19)
    expect(s.p0PendingHumanReview).toBe(5)
    expect(s.routeGovernance).toBe('34/34/5/0/1/1')
    expect(s.backendRouteChanges).toBe(0)
    expect(s.productionRuntime).toBe('NO-GO')
    expect(s.webuiExecution).toBe('NO-GO')
    expect(s.approvalActions).toBe('NO-GO')
    expect(s.productionRollout).toBe('NO-GO')
    expect(s.targetBStatus).toBe('NOT_STARTED_OR_NO_GO')
    expect(s.targetBReason).toContain('unauthorized')
  })

  it('completion cards include the required verdicts and counts', () => {
    const cards = buildTargetACompletionCards()
    const byLabel = new Map(cards.map((c) => [c.label, c]))
    expect(byLabel.get('Target A Status')!.value).toBe('COMPLETE')
    expect(byLabel.get('P0 resolved')!.value).toBe(0)
    expect(byLabel.get('Route governance')!.value).toBe('34/34/5/0/1/1')
    expect(byLabel.get('Production runtime')!.value).toBe('NO-GO')
    expect(byLabel.get('Production readiness')!.value).toBe('NO-GO')
    expect(byLabel.get('Target B')!.value).toBe('deferred')
  })
})

describe('targetACompletion view-model — capability matrix', () => {
  it('projects exactly 15 capability rows', () => {
    const rows = buildTargetACapabilityMatrix()
    expect(rows).toHaveLength(15)
    const names = rows.map((r) => r.capability)
    for (const required of [
      'Static Descriptor Registry',
      'Runtime Governance CLI',
      'Runtime Governance WebUI',
      'Human Review Governance WebUI',
      'Governance Hub',
    ]) {
      expect(names, `missing ${required}`).toContain(required)
    }
  })

  it('every capability row adds no route and authorizes no production', () => {
    for (const r of buildTargetACapabilityMatrix()) {
      expect(r.routeImpact).toBe('No new route')
      const pi = r.productionImpact.toLowerCase()
      expect(pi).not.toContain('authorizes production')
      expect(pi).not.toContain('production authorized')
      expect(pi).not.toMatch(/\bgo\b/)
      expect(r.targetAContribution === 'complete' || r.targetAContribution === 'implemented' || r.targetAContribution === 'partial').toBe(true)
      expect(r.targetBImpact.length).toBeGreaterThan(0)
    }
  })
})

describe('targetACompletion view-model — readiness checklist', () => {
  it('projects exactly 15 readiness items, all pass and none blocking', () => {
    const items = buildTargetAReadinessChecklist()
    expect(items).toHaveLength(15)
    for (const item of items) {
      expect(item.status).toBe('pass')
      expect(item.blockingForTargetA).toBe(false)
    }
  })

  it('no readiness evidence summary claims production readiness', () => {
    for (const item of buildTargetAReadinessChecklist()) {
      expect(item.evidenceSummary.toLowerCase()).not.toContain('production ready')
      expect(item.evidenceSummary.toLowerCase()).not.toContain('authorized')
    }
  })
})

describe('targetACompletion view-model — Target B deferred matrix', () => {
  it('projects exactly 28 deferred rows, every one NO-GO', () => {
    const rows = buildTargetBDeferredMatrix()
    expect(rows).toHaveLength(28)
    for (const r of rows) {
      expect(r.currentStatus).toBe('NO-GO')
      expect(r.targetAImpact).toBe('not required')
      expect(r.targetBImpact).toBe('required / future phase')
      expect(r.whyDeferred.length).toBeGreaterThan(0)
      expect(r.requiredBeforeStart.length).toBeGreaterThan(0)
    }
  })

  it('the deferred matrix covers every required still-not-authorized item', () => {
    const joined = buildTargetBDeferredMatrix()
      .map((r) => r.item)
      .join(' ')
      .toLowerCase()
    for (const required of [
      'production plugin runtime',
      'arbitrary plugin loading',
      'user-uploaded plugins',
      'remote registry',
      'marketplace',
      'external network',
      'webui execution route',
      'webui run button',
      'production rollout',
      'cli input-file reading',
      'cli output-file writing',
      'persistent runtime audit store',
    ]) {
      expect(joined, `missing deferred item ${required}`).toContain(required)
    }
  })
})

describe('targetACompletion view-model — release readiness + acceptance + text', () => {
  it('release readiness is green/unchanged and never implies production', () => {
    const r = buildTargetACompletionViewModel().releaseReadiness
    expect(r.frontendTests).toBe('green')
    expect(r.backendIsolationTests).toBe('green')
    expect(r.runtimeCliTests).toBe('green')
    expect(r.descriptorRegistryTests).toBe('green')
    expect(r.memoryCheck).toBe('PASS')
    expect(r.routeGovernance).toBe('unchanged')
    expect(r.productionSafety).toBe('unchanged')
    expect(r.worktreeExpectedCleanAfterCommit).toBe(true)
    expect(r.claudeTracked).toBe(false)
  })

  it('acceptance verdict is PASS with non-empty why-pass and why-not-production', () => {
    const a = buildTargetACompletionViewModel().acceptance
    expect(a.verdict).toBe('PASS')
    expect(a.whyPass.length).toBeGreaterThanOrEqual(3)
    expect(a.whyNotProduction.length).toBeGreaterThanOrEqual(3)
    const joined = a.whyNotProduction.join(' ').toLowerCase()
    expect(joined).toContain('p0 resolved')
    expect(joined).toContain('production runtime')
  })

  it('summary text is deterministic, contains the frozen counts, and states NO-GO / not production', () => {
    const text = buildTargetASummaryText()
    expect(text).toContain('Target A: COMPLETE')
    expect(text).toContain('34/34/5/0/1/1')
    expect(text).toContain('NO-GO')
    expect(text.toLowerCase()).toContain('not production authorization')
    expect(buildTargetASummaryText()).toBe(text)
  })

  it('the full hub view model carries a targetA sub-model', () => {
    const vm = buildGovernanceHubViewModel()
    expect(vm.targetA).toBeDefined()
    expect(vm.targetA.schemaVersion).toBe('phase-3m-target-a-v1')
    expect(vm.targetA.summary.targetStatus).toBe('COMPLETE')
  })
})

describe('targetACompletion view-model — immutability', () => {
  it('the canonical manifest exports are frozen', () => {
    expect(Object.isFrozen(TARGET_A_COMPLETION_SUMMARY)).toBe(true)
    expect(Object.isFrozen(TARGET_A_CAPABILITY_MATRIX)).toBe(true)
    expect(Object.isFrozen(TARGET_A_CAPABILITY_MATRIX[0])).toBe(true)
    expect(Object.isFrozen(TARGET_A_READINESS_CHECKLIST)).toBe(true)
    expect(Object.isFrozen(TARGET_B_DEFERRED_MATRIX)).toBe(true)
    expect(Object.isFrozen(TARGET_A_ACCEPTANCE)).toBe(true)
    expect(Object.isFrozen(TARGET_A_RELEASE_READINESS)).toBe(true)
  })

  it('mutating a returned summary cannot flip resolved / production / Target B', () => {
    const s = buildTargetACompletionSummary()
    s.p0Resolved = 24 as unknown as 0
    s.productionRuntime = 'GO' as unknown as 'NO-GO'
    s.targetBStatus = 'STARTED' as unknown as 'NOT_STARTED_OR_NO_GO'
    s.productionReadiness = '100' as unknown as 'NO-GO'
    const fresh = buildTargetACompletionSummary()
    expect(fresh.p0Resolved).toBe(0)
    expect(fresh.productionRuntime).toBe('NO-GO')
    expect(fresh.targetBStatus).toBe('NOT_STARTED_OR_NO_GO')
    expect(fresh.productionReadiness).toBe('NO-GO')
  })

  it('mutating a returned capability row cannot reach the canonical matrix', () => {
    const before = TARGET_A_CAPABILITY_MATRIX[0]!.capability
    const rows = buildTargetACapabilityMatrix()
    rows[0]!.capability = 'tampered'
    rows[0]!.productionImpact = 'production authorized'
    expect(rows[0]!.capability).toBe('tampered')
    expect(TARGET_A_CAPABILITY_MATRIX[0]!.capability).toBe(before)
    const fresh = buildTargetACapabilityMatrix()
    expect(fresh[0]!.capability).toBe(before)
    expect(fresh[0]!.productionImpact).not.toContain('authorized')
  })

  it('mutating a returned readiness list cannot flip pass states', () => {
    const items = buildTargetAReadinessChecklist()
    items[0]!.status = 'fail' as unknown as 'pass'
    items.length = 0
    const fresh = buildTargetAReadinessChecklist()
    expect(fresh).toHaveLength(15)
    expect(fresh[0]!.status).toBe('pass')
  })

  it('mutating a returned deferred matrix cannot drain or authorize the canonical list', () => {
    const rows = buildTargetBDeferredMatrix()
    rows[0]!.currentStatus = 'GO' as unknown as 'NO-GO'
    rows.length = 0
    const fresh = buildTargetBDeferredMatrix()
    expect(fresh).toHaveLength(28)
    expect(fresh[0]!.currentStatus).toBe('NO-GO')
  })

  it('mutating a returned acceptance cannot flip the verdict or drop a not-production reason', () => {
    const a = buildTargetACompletionViewModel().acceptance
    a.verdict = 'PRODUCTION_GO' as unknown as 'PASS'
    a.whyNotProduction.length = 0
    const fresh = buildTargetACompletionViewModel().acceptance
    expect(fresh.verdict).toBe('PASS')
    expect(fresh.whyNotProduction.length).toBeGreaterThanOrEqual(3)
  })
})

describe('targetACompletion view-model — defense-in-depth redactor (corpus)', () => {
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
    'target_b_authorized=true',
    'production_runtime_go=true',
  ]

  it.each(CORPUS)('masks secret-shaped / fake-approval value %s', (value) => {
    expect(redactGovernanceHubValue(value)).toBe('[REDACTED]')
  })

  it('leaves safe Target A governance text intact', () => {
    expect(redactGovernanceHubValue('Target A: COMPLETE')).toContain('COMPLETE')
    expect(redactGovernanceHubValue('Dev-only runtime prototype complete')).toContain('prototype')
    expect(redactGovernanceHubValue('Target B remains NO-GO')).toContain('NO-GO')
  })

  it('the static manifest carries no secret-shaped Target A text', () => {
    const texts: string[] = []
    texts.push(TARGET_A_COMPLETION_SUMMARY.targetBReason)
    for (const r of TARGET_A_CAPABILITY_MATRIX) texts.push(r.evidence, r.tests, r.targetBImpact)
    for (const r of TARGET_B_DEFERRED_MATRIX) texts.push(r.whyDeferred, r.requiredBeforeStart)
    for (const line of TARGET_A_ACCEPTANCE.whyNotProduction) texts.push(line)
    for (const c of CORPUS) {
      for (const text of texts) {
        expect(text).not.toContain(c)
      }
    }
  })
})
