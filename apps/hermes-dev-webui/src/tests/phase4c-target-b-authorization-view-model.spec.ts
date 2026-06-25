/**
 * Phase 4C — Target B Authorization view-model tests.
 *
 * Asserts the pure view-model projections for the read-only Target B
 * Authorization Package region are deterministic, frozen, value-free, and
 * defense-in-depth redacted, and that every authorization verdict stays NO-GO,
 * the readiness stays BLOCKED, the trust token stays not provisioned, P0
 * resolved stays 0, the production signature verifier stays not authorized, and
 * the route baseline stays unchanged (34/34/5/0/1/1).
 */
import { describe, it, expect } from 'vitest'
import {
  buildTargetBAuthorizationViewModel,
  buildTargetBAuthorizationSummary,
  buildTargetBAuthorizationLayers,
  buildTargetBAuthorizationSummaryText,
  buildTargetBP0GateCoverage,
  buildTargetBEnablementReadiness,
  filterTargetBAuthorizationLayers,
  allTargetBAuthorizationVerdictsNoGo,
  allTargetBAuthorizationLayersUnauthorized,
  targetBAuthorizationStaysBlocked,
  redactTargetBAuthorizationValue,
} from '@/lib/targetBAuthorizationViewModel'
import {
  TARGET_B_AUTHORIZATION_SUMMARY,
  TARGET_B_AUTHORIZATION_LAYERS,
  TARGET_B_P0_GATE_COVERAGE_ROWS,
} from '@/constants/targetBAuthorizationManifest'

describe('targetBAuthorization view-model (Phase 4C) — determinism + frozen invariants', () => {
  it('is deterministic — two builds are deeply equal', () => {
    const a = buildTargetBAuthorizationViewModel()
    const b = buildTargetBAuthorizationViewModel()
    expect(JSON.stringify(a)).toEqual(JSON.stringify(b))
  })

  it('the frozen summary is AUTHORIZATION_PACKAGE_IMPLEMENTED / readiness BLOCKED with every authorization NO-GO', () => {
    const s = buildTargetBAuthorizationSummary()
    expect(s.authorizationStatus).toBe('AUTHORIZATION_PACKAGE_IMPLEMENTED')
    expect(s.readinessStatus).toBe('BLOCKED')
    expect(s.productionEnablementAllowed).toBe(false)
    expect(s.productionRuntime).toBe('NO-GO')
    expect(s.trustTokenProvisioned).toBe(false)
    expect(s.productionSignatureVerifierAuthorized).toBe(false)
    expect(s.p0Total).toBe(24)
    expect(s.p0Resolved).toBe(0)
    expect(allTargetBAuthorizationVerdictsNoGo(s)).toBe(true)
  })

  it('the 11 authorization layers are all unauthorized', () => {
    const layers = buildTargetBAuthorizationLayers()
    expect(layers.length).toBe(11)
    expect(allTargetBAuthorizationLayersUnauthorized(layers)).toBe(true)
    for (const l of layers) {
      expect(l.authorized).toBe(false)
    }
  })

  it('the P0 gate coverage keeps all 5 pending gates unresolved with resolved delta 0', () => {
    const cov = buildTargetBP0GateCoverage()
    expect(cov.p0Resolved).toBe(0)
    expect(cov.pendingHumanReview).toBe(5)
    expect(cov.resolvedCountDelta).toBe(0)
    expect(cov.coverage.length).toBe(5)
    for (const g of cov.coverage) {
      expect(g.resolved).toBe(false)
      expect(g.hasHumanApproval).toBe(false)
      expect(g.hasTrustToken).toBe(false)
    }
  })

  it('the enablement readiness stays BLOCKED and production enablement not allowed', () => {
    const er = buildTargetBEnablementReadiness()
    expect(er.readinessStatus).toBe('BLOCKED')
    expect(er.productionEnablementAllowed).toBe(false)
    expect(er.allGatesPass).toBe(false)
    expect(targetBAuthorizationStaysBlocked(er)).toBe(true)
    expect(er.blockers.length).toBe(11)
  })

  it('the layer filter is a pure client-side selector on static data', () => {
    const all = filterTargetBAuthorizationLayers('all')
    expect(all.length).toBe(11)
    const design = filterTargetBAuthorizationLayers('DESIGN_READY_ONLY')
    for (const l of design) expect(l.status).toBe('DESIGN_READY_ONLY')
  })

  it('defense-in-depth redactor masks secret-shaped / fake-authorization substrings', () => {
    expect(redactTargetBAuthorizationValue('sk-123')).toBe('[REDACTED]')
    expect(redactTargetBAuthorizationValue('target_b_authorized=true')).toBe('[REDACTED]')
    expect(redactTargetBAuthorizationValue('trust_token=fake')).toBe('[REDACTED]')
  })

  it('immutability — external mutation cannot reach the canonical manifest', () => {
    const vm1 = buildTargetBAuthorizationViewModel()
    const vm2 = buildTargetBAuthorizationViewModel()
    expect(vm2.summary.readinessStatus).toBe('BLOCKED')
    // Mutating vm1 cannot affect vm2 or the manifest.
    vm1.summary.readinessStatus = 'CORRUPTED' as never
    expect(vm2.summary.readinessStatus).toBe('BLOCKED')
    expect(TARGET_B_AUTHORIZATION_SUMMARY.readinessStatus).toBe('BLOCKED')
  })

  it('the summary text is BLOCKED, contains the route baseline, and no forbidden token', () => {
    const text = buildTargetBAuthorizationSummaryText()
    expect(text).toContain('BLOCKED')
    expect(text).toContain('34/34/5/0/1/1')
    for (const token of [
      'sk-',
      'Bearer ',
      'trust_token=fake',
      'production_runtime_go=true',
      'target_b_authorized=true',
      'approved_by_ai=true',
    ]) {
      expect(text).not.toContain(token)
    }
  })

  it('the frozen manifest P0 coverage rows cover exactly the pending gates', () => {
    const ids = TARGET_B_P0_GATE_COVERAGE_ROWS.map((r) => r.gateId)
    expect(ids).toEqual(['P0-15', 'P0-16', 'P0-18', 'P0-19', 'P0-22'])
  })

  it('the frozen manifest layers count matches the view-model', () => {
    expect(TARGET_B_AUTHORIZATION_LAYERS.length).toBe(11)
  })
})
