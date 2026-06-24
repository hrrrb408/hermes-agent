/**
 * Phase 3L — Governance Hub view-model tests.
 *
 * Asserts the pure view-model projections are deterministic, carry the frozen
 * summary (24 / 0 / 19 / 5, every authorization NO-GO / not-authorized), the
 * frozen route counts (34/34/5/0/1/1, every new-route flag 0), the all-False
 * production-safety block, the 8-row evidence trail, the deferred list, the
 * cross-links, immutability (an external mutation cannot reach the canonical
 * manifest), and that the defense-in-depth redactor masks every secret-shaped /
 * production-path-shaped / fake-approval-shaped substring (redaction corpus).
 */
import { describe, it, expect } from 'vitest'

import {
  buildGovernanceHubViewModel,
  buildGovernanceHubSummary,
  buildGovernanceHubSummaryCards,
  buildGovernanceHubModules,
  buildGovernanceHubRouteSummary,
  buildGovernanceHubProductionSafety,
  buildGovernanceHubDecisions,
  buildGovernanceHubDecisionRows,
  buildGovernanceHubEvidenceTrail,
  buildGovernanceHubDeferredItems,
  buildGovernanceHubCrossLinks,
  buildGovernanceHubForbiddenActions,
  buildGovernanceHubAllowedUiActions,
  buildGovernanceHubStatusBadges,
  buildGovernanceHubBoundaryItems,
  buildGovernanceHubSummaryText,
  filterGovernanceHubModules,
  resolveCrossLinkTarget,
  everyDecisionHolds,
  noModuleAuthorizesProduction,
  redactGovernanceHubValue,
  sanitizeGovernanceHubDisplayText,
  GOVERNANCE_HUB_MODULE_FILTER_OPTIONS,
} from '@/lib/governanceHubViewModel'
import {
  GOVERNANCE_HUB_SUMMARY,
  GOVERNANCE_HUB_MODULES,
  GOVERNANCE_HUB_ROUTE_SUMMARY,
  GOVERNANCE_HUB_DECISION_ROWS,
  GOVERNANCE_HUB_DEFERRED_ITEMS,
} from '@/constants/governanceHubManifest'

describe('governanceHubViewModel (Phase 3L) — determinism + summary', () => {
  it('is deterministic — two builds are deeply equal', () => {
    const a = buildGovernanceHubViewModel()
    const b = buildGovernanceHubViewModel()
    expect(JSON.stringify(a)).toEqual(JSON.stringify(b))
  })

  it('the frozen summary projects 24 / 0 / 19 / 5 and every authorization NO-GO', () => {
    const s = buildGovernanceHubSummary()
    expect(s.currentPhase).toBe('Phase 3L')
    expect(s.runtimeGovernanceStatus).toBe('COMPLETE')
    expect(s.humanReviewGovernanceStatus).toBe('IMPLEMENTED')
    expect(s.p0Total).toBe(24)
    expect(s.p0Resolved).toBe(0)
    expect(s.p0Partial).toBe(19)
    expect(s.p0PendingHumanReview).toBe(5)
    expect(s.routeGovernanceUnchanged).toBe(true)
    expect(s.productionGatewayUntouched).toBe(true)
    expect(s.productionRuntimeAuthorization).toBe('NO-GO')
    expect(s.implementationAuthorization).toBe('NO-GO')
    expect(s.productionRollout).toBe('NO-GO')
  })

  it('summary cards include the required counts and verdicts', () => {
    const cards = buildGovernanceHubSummaryCards()
    const byLabel = new Map(cards.map((c) => [c.label, c]))
    expect(byLabel.get('Runtime Governance')!.value).toBe('COMPLETE')
    expect(byLabel.get('Human Review Governance')!.value).toBe('IMPLEMENTED')
    expect(byLabel.get('P0 gates')!.value).toBe(24)
    expect(byLabel.get('P0 resolved')!.value).toBe(0)
    expect(byLabel.get('Pending human review')!.value).toBe(5)
    expect(byLabel.get('Route governance')!.value).toBe('34/34/5/0/1/1')
    expect(byLabel.get('Production runtime')!.value).toBe('NO-GO')
    expect(byLabel.get('Production rollout')!.value).toBe('NO-GO')
    expect(byLabel.get('Backend route changes')!.value).toBe(0)
  })
})

describe('governanceHubViewModel — modules + filters', () => {
  it('projects exactly 10 modules', () => {
    const modules = buildGovernanceHubModules()
    expect(modules).toHaveLength(10)
    const names = modules.map((m) => m.name)
    expect(names).toContain('Governance Hub')
    expect(names).toContain('Runtime Governance WebUI')
    expect(names).toContain('Human Review Governance WebUI')
  })

  it('every module authorizes no production and is read-only', () => {
    const modules = buildGovernanceHubModules()
    expect(noModuleAuthorizesProduction(modules)).toBe(true)
    for (const m of modules) {
      expect(m.routeImpact).toBe('No new route')
      expect(m.productionImpact).toBe('No production authorization')
      expect(m.authorizationImpact).toBe('NO-GO')
      expect(m.readOnly).toBe(true)
    }
  })

  it('exposes exactly four module filter options', () => {
    expect(GOVERNANCE_HUB_MODULE_FILTER_OPTIONS.map((o) => o.key)).toEqual([
      'all',
      'COMPLETE',
      'IMPLEMENTED',
      'READ_ONLY',
    ])
  })

  it('the All filter returns 10 modules; COMPLETE returns >= 1; IMPLEMENTED returns >= 1', () => {
    expect(filterGovernanceHubModules('all')).toHaveLength(10)
    expect(filterGovernanceHubModules('COMPLETE').length).toBeGreaterThanOrEqual(1)
    expect(filterGovernanceHubModules('IMPLEMENTED').length).toBeGreaterThanOrEqual(1)
    for (const m of filterGovernanceHubModules('COMPLETE')) {
      expect(m.status).toBe('COMPLETE')
    }
  })
})

describe('governanceHubViewModel — route + production safety + decisions', () => {
  it('projects the frozen route counts (every new-route flag 0)', () => {
    const r = buildGovernanceHubRouteSummary()
    expect(r.openapiPaths).toBe(34)
    expect(r.runtimeRoutes).toBe(34)
    expect(r.toolGetRoutes).toBe(5)
    expect(r.toolWriteHttpRoutes).toBe(0)
    expect(r.toolDryRunRoutes).toBe(1)
    expect(r.toolExecutionRoutes).toBe(1)
    expect(r.newHttpRoutes).toBe(0)
    expect(r.newToolWriteRoutes).toBe(0)
    expect(r.newProviderRoutes).toBe(0)
    expect(r.newPluginRoutes).toBe(0)
    expect(r.newRuntimeRoutes).toBe(0)
    expect(r.format).toBe('34/34/5/0/1/1')
  })

  it('projects the all-False production-safety block', () => {
    const s = buildGovernanceHubProductionSafety()
    expect(s.productionGatewayTouched).toBe(false)
    expect(s.productionGatewayExpectedUnchanged).toBe(true)
    expect(s.devGatewayStarted).toBe(false)
    expect(s.dashboardStarted).toBe(false)
    expect(s.ports5180And5181Bound).toBe(false)
    expect(s.productionHomeAccess).toBe(false)
    expect(s.productionStateDbAccess).toBe(false)
    expect(s.externalNetwork).toBe(false)
    expect(s.realSecretRead).toBe(false)
  })

  it('projects the frozen NO-GO decision block and every decision row holds', () => {
    const d = buildGovernanceHubDecisions()
    expect(d.implementationAuthorization).toBe('NO-GO')
    expect(d.phase3iProductionAuthorization).toBe('NOT_AUTHORIZED')
    expect(d.productionRuntimeAuthorization).toBe('NO-GO')
    expect(d.newBackendRoute).toBe('NO-GO')
    expect(d.approvalBackendRoute).toBe('NO-GO')
    expect(d.webuiExecutionRoute).toBe('NO-GO')
    expect(d.webuiApprovalAction).toBe('NO-GO')
    expect(d.productionRollout).toBe('NO-GO')
    const rows = buildGovernanceHubDecisionRows()
    expect(everyDecisionHolds(rows)).toBe(true)
  })
})

describe('governanceHubViewModel — evidence + deferred + cross-links + actions', () => {
  it('projects the 8-phase evidence trail, each with prove / does-not-prove / partial impact', () => {
    const trail = buildGovernanceHubEvidenceTrail()
    expect(trail).toHaveLength(8)
    const phases = trail.map((s) => s.phase)
    expect(phases).toContain('Phase 3D')
    expect(phases).toContain('Phase 3L')
    for (const s of trail) {
      expect(s.completedDeliverable.trim().length).toBeGreaterThan(0)
      expect(s.whatItProves.trim().length).toBeGreaterThan(0)
      expect(s.whatItDoesNotProve.trim().length).toBeGreaterThan(0)
      expect(s.authorizationImpact).toBe('Partial evidence only — no production authorization')
    }
  })

  it('the deferred list includes all the required still-not-authorized items', () => {
    const items = buildGovernanceHubDeferredItems()
    const joined = items.join(' ').toLowerCase()
    for (const required of [
      'production plugin runtime',
      'arbitrary plugin loading',
      'user-uploaded plugins',
      'remote registry',
      'marketplace',
      'external network',
      'new backend route',
      'approval backend route',
      'authorization backend route',
      'webui execution route',
      'webui approve',
      'production rollout',
      'cli input-file reading',
      'cli output-file writing',
      'persistent runtime audit store',
    ]) {
      expect(joined, `missing deferred item ${required}`).toContain(required)
    }
  })

  it('cross-links resolve to the two existing sections', () => {
    const links = buildGovernanceHubCrossLinks()
    const targets = links.map((l) => l.target)
    expect(targets).toEqual(['runtimeGovernance', 'humanReview'])
    expect(resolveCrossLinkTarget('runtimeGovernance')).toBe('runtimeGovernance')
    expect(resolveCrossLinkTarget('humanReview')).toBe('humanReview')
    expect(resolveCrossLinkTarget('governanceHub')).toBeUndefined()
    expect(resolveCrossLinkTarget(null)).toBeUndefined()
  })

  it('forbidden actions include approve / authorize / production rollout; allowed actions are read-only', () => {
    const forbidden = buildGovernanceHubForbiddenActions().join(' ').toLowerCase()
    expect(forbidden).toContain('approve')
    expect(forbidden).toContain('authorize')
    expect(forbidden).toContain('production rollout')
    expect(forbidden).toContain('arbitrary plugin loading')
    expect(forbidden).toContain('marketplace')
    const allowed = buildGovernanceHubAllowedUiActions().join(' ').toLowerCase()
    expect(allowed).toContain('copy summary text')
    expect(allowed).toContain('filter modules by status')
  })

  it('status badges and boundary items project frozen, labelled rows', () => {
    expect(buildGovernanceHubStatusBadges().map((b) => b.label)).toEqual([
      'READ-ONLY',
      'UNIFIED CONTROL CENTER',
      'NO PRODUCTION RUNTIME',
      'NO APPROVAL ACTIONS',
      'ROUTES UNCHANGED',
    ])
    const items = buildGovernanceHubBoundaryItems()
    expect(items.length).toBeGreaterThan(0)
    for (const it of items) {
      expect(it.kind === 'lock' || it.kind === 'ban').toBe(true)
      expect(it.label.trim().length).toBeGreaterThan(0)
    }
  })

  it('summary text is deterministic and redacts nothing safe but contains the frozen counts', () => {
    const text = buildGovernanceHubSummaryText()
    expect(text).toContain('Governance Hub')
    expect(text).toContain('34/34/5/0/1/1')
    expect(text).toContain('NO-GO')
    expect(buildGovernanceHubSummaryText()).toBe(text)
  })

  it('route governance baseline + backend-routes-unchanged flag', () => {
    const vm = buildGovernanceHubViewModel()
    expect(vm.routeGovernanceBaseline).toBe('34/34/5/0/1/1')
    expect(vm.backendRoutesChanged).toBe(false)
    expect(vm.schemaVersion).toBe('phase-3l-governance-hub-v1')
  })
})

describe('governanceHubViewModel — immutability', () => {
  it('the canonical manifest exports are frozen', () => {
    expect(Object.isFrozen(GOVERNANCE_HUB_SUMMARY)).toBe(true)
    expect(Object.isFrozen(GOVERNANCE_HUB_MODULES)).toBe(true)
    expect(Object.isFrozen(GOVERNANCE_HUB_MODULES[0])).toBe(true)
    expect(Object.isFrozen(GOVERNANCE_HUB_ROUTE_SUMMARY)).toBe(true)
    expect(Object.isFrozen(GOVERNANCE_HUB_DECISION_ROWS)).toBe(true)
    expect(Object.isFrozen(GOVERNANCE_HUB_DEFERRED_ITEMS)).toBe(true)
  })

  it('mutating a returned module does not mutate the canonical manifest', () => {
    const before = GOVERNANCE_HUB_MODULES[0]!.name
    const modules = buildGovernanceHubModules()
    modules[0]!.name = 'tampered'
    expect(modules[0]!.name).toBe('tampered')
    expect(GOVERNANCE_HUB_MODULES[0]!.name).toBe(before)
  })

  it('mutating a returned route summary cannot flip the new-route counts', () => {
    const r = buildGovernanceHubRouteSummary()
    r.newHttpRoutes = 99 as unknown as 0
    const fresh = buildGovernanceHubRouteSummary()
    expect(fresh.newHttpRoutes).toBe(0)
    expect(GOVERNANCE_HUB_ROUTE_SUMMARY.newHttpRoutes).toBe(0)
  })

  it('mutating a returned deferred list does not drain the canonical list', () => {
    const items = buildGovernanceHubDeferredItems()
    items.push('approve')
    items.length = 0
    expect(GOVERNANCE_HUB_DEFERRED_ITEMS.length).toBeGreaterThan(0)
    expect(buildGovernanceHubDeferredItems().includes('production rollout')).toBe(true)
  })

  it('mutating a returned summary cannot flip resolved / NO-GO values', () => {
    const s = buildGovernanceHubSummary()
    s.p0Resolved = 24 as unknown as 0
    s.implementationAuthorization = 'GO' as unknown as 'NO-GO'
    const fresh = buildGovernanceHubSummary()
    expect(fresh.p0Resolved).toBe(0)
    expect(fresh.implementationAuthorization).toBe('NO-GO')
  })
})

describe('defense-in-depth redactor (corpus)', () => {
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
    expect(redactGovernanceHubValue(value)).toBe('[REDACTED]')
  })

  it('sanitizeGovernanceHubDisplayText is a stable alias of redactGovernanceHubValue', () => {
    for (const c of CORPUS) {
      expect(sanitizeGovernanceHubDisplayText(c)).toBe('[REDACTED]')
    }
  })

  it('leaves safe governance text intact', () => {
    expect(redactGovernanceHubValue('No implementation authorization')).toContain('authorization')
    expect(redactGovernanceHubValue('Governance Hub unified control center')).toContain('Governance')
  })

  it('the static manifest carries no secret-shaped module text', () => {
    for (const m of GOVERNANCE_HUB_MODULES) {
      const texts = [m.name, m.evidenceSummary]
      for (const text of texts) {
        for (const c of CORPUS) {
          expect(text).not.toContain(c)
        }
      }
    }
  })
})
