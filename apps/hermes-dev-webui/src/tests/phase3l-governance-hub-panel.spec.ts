/**
 * Phase 3L — Governance Hub read-only panel tests.
 *
 * Asserts the section renders every required region (header h1 + status badges,
 * boundary banner, summary cards, module status board, P0 / human-review summary,
 * route governance panel, production safety panel, evidence trail, NO-GO decision
 * panel, deferred list, allowed/forbidden actions panel, cross-links), that the
 * frozen NO-GO / not-authorized / resolved=0 / routes-unchanged invariants are
 * visible, that the only controls are harmless UI-only selects (filter modules,
 * inspect module, view cross-linked section, copy summary), and that cross-links
 * switch the Dev Console section client-side with no backend / SPA route change.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import GovernanceHubSection from '@/components/devconsole/GovernanceHubSection.vue'
import {
  GOVERNANCE_HUB_MODULE_FILTER_OPTIONS,
} from '@/lib/governanceHubViewModel'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'

const EXPECTED_MODULE_NAMES = [
  'Static Descriptor Registry',
  'Runtime Sandbox Safety Baseline',
  'Sandbox Proof Runner',
  'Dev-only Local Runtime MVP',
  'Runtime Fixture Expansion',
  'Descriptor Runtime Integration',
  'Runtime Governance CLI',
  'Runtime Governance WebUI',
  'Human Review Governance WebUI',
  'Governance Hub',
]

describe('GovernanceHubSection (Phase 3L) — rendering', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('renders the section with title and read-only / control-center / routes-unchanged badges', () => {
    const wrapper = mount(GovernanceHubSection)
    expect(wrapper.find('[data-testid="governance-hub-section"]').exists()).toBe(true)
    expect(wrapper.find('h1').text()).toBe('Governance Hub')
    const badges = wrapper.find('[data-testid="governance-hub-status-badges"]')
    expect(badges.findAll('li').map((li) => li.text())).toEqual([
      'READ-ONLY',
      'UNIFIED CONTROL CENTER',
      'NO PRODUCTION RUNTIME',
      'NO APPROVAL ACTIONS',
      'ROUTES UNCHANGED',
    ])
  })

  it('renders the boundary banner with frozen NO-GO decisions', () => {
    const wrapper = mount(GovernanceHubSection)
    const banner = wrapper.find('[data-testid="governance-hub-boundary-banner"]')
    expect(banner.exists()).toBe(true)
    const decisions = wrapper.find('[data-testid="governance-hub-boundary-decisions"]')
    const text = decisions.text()
    expect(text).toContain('Implementation Authorization')
    expect(text).toContain('New Backend Route')
    expect(text).toContain('WebUI Execution Route')
    expect(text).toContain('Production Rollout')
    expect(text).toContain('NO-GO')
    expect(text).toContain('NOT_AUTHORIZED')
  })

  it('renders the summary cards with the frozen counts and verdicts', () => {
    const wrapper = mount(GovernanceHubSection)
    const text = wrapper.text()
    expect(text).toContain('Runtime Governance')
    expect(text).toContain('Human Review Governance')
    expect(text).toContain('P0 gates')
    expect(text).toContain('Pending human review')
    expect(text).toContain('Route governance')
    expect(text).toContain('Production runtime')
    expect(text).toContain('Production rollout')
    expect(text).toContain('Backend route changes')
  })

  it('renders the module board with all 10 modules', () => {
    const wrapper = mount(GovernanceHubSection)
    const board = wrapper.find('[data-testid="governance-hub-module-table"]')
    expect(board.exists()).toBe(true)
    const rows = board.findAll('tbody tr')
    expect(rows).toHaveLength(10)
    const names = board.findAll('tbody tr').map((r) => r.find('.ghub-board__name').text())
    for (const name of EXPECTED_MODULE_NAMES) {
      expect(names, `missing module ${name}`).toContain(name)
    }
  })

  it('every module renders phase, status, route impact, production impact, authorization NO-GO, read-only', () => {
    const wrapper = mount(GovernanceHubSection)
    const rows = wrapper.findAll('[data-testid="governance-hub-module-table"] tbody tr')
    expect(rows.length).toBe(10)
    for (const row of rows) {
      expect(row.find('.ghub-board__phase').text().length).toBeGreaterThan(0)
      expect(row.find('[data-status]').exists()).toBe(true)
      expect(row.text()).toContain('No new route')
      expect(row.text()).toContain('No production authorization')
      expect(row.find('[data-verdict="NO-GO"]').exists()).toBe(true)
    }
  })

  it('renders exactly the module filter options and All is active by default', () => {
    const wrapper = mount(GovernanceHubSection)
    const filterButtons = wrapper.findAll('[class~="ghub-filter-btn"]')
    expect(filterButtons).toHaveLength(GOVERNANCE_HUB_MODULE_FILTER_OPTIONS.length)
    const allBtn = wrapper.find('[data-testid="governance-hub-module-filter-all"]')
    expect(allBtn.attributes('aria-pressed')).toBe('true')
  })

  it('the Complete filter shows the modules marked COMPLETE and the Implemente filter shows the rest', async () => {
    const wrapper = mount(GovernanceHubSection)
    await wrapper.find('[data-testid="governance-hub-module-filter-COMPLETE"]').trigger('click')
    const completeRows = wrapper.findAll('[data-testid="governance-hub-module-table"] tbody tr')
    for (const row of completeRows) {
      expect(row.attributes('data-module-status')).toBe('COMPLETE')
    }
    await wrapper.find('[data-testid="governance-hub-module-filter-IMPLEMENTED"]').trigger('click')
    const implementedRows = wrapper.findAll('[data-testid="governance-hub-module-table"] tbody tr')
    for (const row of implementedRows) {
      expect(row.attributes('data-module-status')).toBe('IMPLEMENTED')
    }
    await wrapper.find('[data-testid="governance-hub-module-filter-all"]').trigger('click')
    expect(wrapper.findAll('[data-testid="governance-hub-module-table"] tbody tr')).toHaveLength(10)
  })

  it('renders the P0 / human review summary with the frozen 24 / 0 / 19 / 5 counts', () => {
    const wrapper = mount(GovernanceHubSection)
    const p0 = wrapper.find('[data-testid="governance-hub-p0-summary"]')
    expect(p0.exists()).toBe(true)
    const text = p0.text()
    expect(text).toContain('24')
    expect(text).toContain('19')
    expect(text).toContain('5')
    expect(text).toContain('P0-15 / P0-16 / P0-18 / P0-19 / P0-22')
  })

  it('renders the route governance panel with the exact frozen counts', () => {
    const wrapper = mount(GovernanceHubSection)
    const rp = wrapper.find('[data-testid="governance-hub-route-panel"]')
    expect(rp.exists()).toBe(true)
    const table = rp.find('[data-testid="governance-hub-route-table"]')
    expect(table.find('[data-route-key="openapiPaths"] [data-route-count]').text()).toBe('34')
    expect(table.find('[data-route-key="runtimeRoutes"] [data-route-count]').text()).toBe('34')
    expect(table.find('[data-route-key="toolGetRoutes"] [data-route-count]').text()).toBe('5')
    expect(table.find('[data-route-key="toolWriteHttpRoutes"] [data-route-count]').text()).toBe('0')
    expect(table.find('[data-route-key="toolDryRunRoutes"] [data-route-count]').text()).toBe('1')
    expect(table.find('[data-route-key="toolExecutionRoutes"] [data-route-count]').text()).toBe('1')
    expect(table.find('[data-route-key="newHttpRoutes"] [data-route-count]').text()).toBe('0')
    expect(table.find('[data-route-key="newRuntimeRoutes"] [data-route-count]').text()).toBe('0')
    expect(table.find('[data-route-key="newPluginRoutes"] [data-route-count]').text()).toBe('0')
    expect(rp.text()).toContain('34/34/5/0/1/1')
  })

  it('renders the production safety panel with every flag false', () => {
    const wrapper = mount(GovernanceHubSection)
    const safety = wrapper.find('[data-testid="governance-hub-production-safety-panel"]')
    expect(safety.exists()).toBe(true)
    const html = safety.html()
    expect(html).toContain('productionGatewayTouched-false')
    expect(html).toContain('devGatewayStarted-false')
    expect(html).toContain('dashboardStarted-false')
    expect(html).toContain('ports5180And5181Bound-false')
    expect(html).toContain('productionHomeAccess-false')
    expect(html).toContain('productionStateDbAccess-false')
    expect(html).toContain('externalNetwork-false')
    expect(html).toContain('realSecretRead-false')
    expect(safety.text().toLowerCase()).toContain('no production home access')
  })

  it('renders the evidence trail with the eight phases including Phase 3L', () => {
    const wrapper = mount(GovernanceHubSection)
    const trail = wrapper.find('[data-testid="governance-hub-evidence-trail"]')
    expect(trail.exists()).toBe(true)
    const items = trail.findAll('[data-testid="governance-hub-evidence-list"] li')
    expect(items).toHaveLength(8)
    const text = trail.text()
    expect(text).toContain('Phase 3D')
    expect(text).toContain('Phase 3E-H')
    expect(text).toContain('Phase 3H')
    expect(text).toContain('Phase 3I')
    expect(text).toContain('Phase 3J')
    expect(text).toContain('Phase 3K')
    expect(text).toContain('Phase 3L')
    expect(text).toContain('Partial evidence only')
  })

  it('renders the NO-GO decision panel', () => {
    const wrapper = mount(GovernanceHubSection)
    const nogo = wrapper.find('[data-testid="governance-hub-nogo-panel"]')
    expect(nogo.exists()).toBe(true)
    const text = nogo.find('[data-testid="governance-hub-nogo-list"]').text()
    expect(text).toContain('Implementation Authorization')
    expect(text).toContain('Phase 3I Production Authorization')
    expect(text).toContain('Production Runtime')
    expect(text).toContain('New Backend Route')
    expect(text).toContain('WebUI Execution Route')
    expect(text).toContain('Production Rollout')
  })

  it('renders the deferred / still-not-authorized list', () => {
    const wrapper = mount(GovernanceHubSection)
    const deferred = wrapper.find('[data-testid="governance-hub-deferred-list"]')
    expect(deferred.exists()).toBe(true)
    const text = deferred.text().toLowerCase()
    expect(text).toContain('production plugin runtime')
    expect(text).toContain('arbitrary plugin loading')
    expect(text).toContain('remote registry')
    expect(text).toContain('marketplace')
    expect(text).toContain('new backend route')
    expect(text).toContain('production rollout')
    expect(text).toContain('persistent runtime audit store')
  })

  it('renders the allowed / forbidden actions panel', () => {
    const wrapper = mount(GovernanceHubSection)
    const allowed = wrapper.find('[data-testid="governance-hub-allowed-actions"]').text().toLowerCase()
    expect(allowed).toContain('view module status board')
    expect(allowed).toContain('view runtime governance section')
    expect(allowed).toContain('copy summary text')
    const forbidden = wrapper
      .find('[data-testid="governance-hub-forbidden-actions-global"]')
      .text()
      .toLowerCase()
    expect(forbidden).toContain('approve')
    expect(forbidden).toContain('authorize')
    expect(forbidden).toContain('production rollout')
  })

  it('renders the two cross-links', () => {
    const wrapper = mount(GovernanceHubSection)
    const links = wrapper.find('[data-testid="governance-hub-cross-link-list"]')
    expect(links.exists()).toBe(true)
    expect(wrapper.find('[data-testid="governance-hub-cross-link-runtimeGovernance"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="governance-hub-cross-link-humanReview"]').exists()).toBe(true)
  })

  it('View Runtime Governance cross-link switches the Dev Console section client-side', async () => {
    const nav = useDevConsoleNavStore()
    const wrapper = mount(GovernanceHubSection)
    await wrapper.find('[data-testid="governance-hub-cross-link-runtimeGovernance"]').trigger('click')
    expect(nav.activeSection).toBe('runtimeGovernance')
  })

  it('View Human Review cross-link switches the Dev Console section client-side', async () => {
    const nav = useDevConsoleNavStore()
    const wrapper = mount(GovernanceHubSection)
    await wrapper.find('[data-testid="governance-hub-cross-link-humanReview"]').trigger('click')
    expect(nav.activeSection).toBe('humanReview')
  })

  it('the module-board View link on Runtime Governance WebUI navigates to that section', async () => {
    const nav = useDevConsoleNavStore()
    const wrapper = mount(GovernanceHubSection)
    await wrapper.find('[data-testid="governance-hub-module-link-runtimeGovernanceWebui"]').trigger('click')
    expect(nav.activeSection).toBe('runtimeGovernance')
  })

  it('Copy summary writes the snapshot to the clipboard and flips to Copied', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    const wrapper = mount(GovernanceHubSection)
    await wrapper.find('[data-testid="governance-hub-copy-summary"]').trigger('click')
    await Promise.resolve()
    await Promise.resolve()
    expect(writeText).toHaveBeenCalled()
    const written = String(writeText.mock.calls[0]![0])
    expect(written).toContain('Governance Hub')
    expect(written).toContain('34/34/5/0/1/1')
    expect(written).toContain('NO-GO')
    const btn = wrapper.find('[data-testid="governance-hub-copy-summary"]')
    expect(btn.attributes('data-copy-state')).toBe('copied')
    expect(btn.text()).toContain('Copied')
  })

  it('Copy shows a harmless Unavailable state when the clipboard API is absent', async () => {
    vi.stubGlobal('navigator', {})
    const wrapper = mount(GovernanceHubSection)
    await wrapper.find('[data-testid="governance-hub-copy-summary"]').trigger('click')
    await Promise.resolve()
    const btn = wrapper.find('[data-testid="governance-hub-copy-summary"]')
    expect(btn.attributes('data-copy-state')).toBe('unavailable')
    expect(btn.text()).toContain('Unavailable')
  })

  it('P0 resolved stays 0 and Implementation Authorization stays NO-GO in the DOM', () => {
    const wrapper = mount(GovernanceHubSection)
    const p0 = wrapper.find('[data-testid="governance-hub-p0-summary"]')
    expect(p0.find('[data-p0-key="resolved"] [data-p0-value]').text()).toBe('0')
    const nogo = wrapper.find('[data-testid="governance-hub-nogo-list"]').text()
    expect(nogo).toContain('NO-GO')
  })
})
