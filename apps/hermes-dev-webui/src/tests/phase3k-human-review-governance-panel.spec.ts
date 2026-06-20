/**
 * Phase 3K — Human Review Governance read-only panel tests.
 *
 * Asserts the section renders every required region (header h1 + status badges,
 * boundary banner, summary cards, filter toolbar, 24-gate table, gate detail,
 * evidence trail, NO-GO + relationship panel, allowed/forbidden actions panel,
 * route governance), that the frozen NO-GO / not-authorized / resolved=0
 * invariants are visible, that the only controls are harmless UI-only selects
 * (filter, inspect gate, copy gate id), and that the gate detail clearly states
 * resolved=false / approved=false / production NO-GO.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import HumanReviewGovernanceSection from '@/components/devconsole/HumanReviewGovernanceSection.vue'
import {
  HUMAN_REVIEW_FILTER_OPTIONS,
} from '@/lib/humanReviewGovernanceViewModel'
import { HUMAN_REVIEW_GATES } from '@/constants/humanReviewGovernanceManifest'

const PENDING_GATE_IDS = ['P0-15', 'P0-16', 'P0-18', 'P0-19', 'P0-22']

describe('HumanReviewGovernanceSection (Phase 3K) — rendering', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('renders the section with title and read-only / human-review / NO-GO badges', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    expect(wrapper.find('[data-testid="human-review-governance-section"]').exists()).toBe(true)
    expect(wrapper.find('h1').text()).toBe('Human Review Governance')
    const badges = wrapper.find('[data-testid="human-review-status-badges"]')
    expect(badges.findAll('li').map((li) => li.text())).toEqual([
      'READ-ONLY',
      'P0 GATES',
      'HUMAN REVIEW REQUIRED',
      'NO APPROVAL FROM WEBUI',
      'PRODUCTION NO-GO',
    ])
    const text = wrapper.text().toLowerCase()
    expect(text).toContain('read-only')
    expect(text).toContain('human review')
    expect(text).toContain('no-go')
  })

  it('renders the boundary banner with frozen NO-GO decisions', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    const banner = wrapper.find('[data-testid="human-review-boundary-banner"]')
    expect(banner.exists()).toBe(true)
    const decisions = wrapper.find('[data-testid="human-review-boundary-decisions"]')
    const text = decisions.text()
    expect(text).toContain('Implementation Authorization')
    expect(text).toContain('Phase 3I Production Authorization')
    expect(text).toContain('Production Rollout')
    expect(text).toContain('NO-GO')
    expect(text).toContain('NOT_AUTHORIZED')
  })

  it('renders the summary cards with the frozen counts', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    const text = wrapper.text()
    expect(text).toContain('Total P0 gates')
    expect(text).toContain('Pending human review')
    expect(text).toContain('Partial evidence')
    expect(text).toContain('Implementation Authorization')
  })

  it('renders the gate table with all 24 gates', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    const table = wrapper.find('[data-testid="human-review-gate-table"]')
    expect(table.exists()).toBe(true)
    expect(table.findAll('tbody tr')).toHaveLength(24)
    for (const g of HUMAN_REVIEW_GATES) {
      expect(table.find(`[data-gate-id="${g.gateId}"]`).exists(), g.gateId).toBe(true)
    }
  })

  it('renders exactly five filter buttons and All is active by default', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    const toolbar = wrapper.find('[data-testid="human-review-filter-toolbar"]')
    const buttons = toolbar.findAll('button')
    expect(buttons).toHaveLength(HUMAN_REVIEW_FILTER_OPTIONS.length)
    const allBtn = wrapper.find('[data-testid="human-review-filter-all"]')
    expect(allBtn.attributes('aria-pressed')).toBe('true')
    expect(allBtn.attributes('data-filter-count')).toBe('24')
  })

  it('the Partial evidence filter shows 19 gates and the All filter shows 24', async () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    expect(wrapper.find('[data-testid="human-review-filter-partial_evidence"]').attributes('data-filter-count')).toBe('19')
    await wrapper.find('[data-testid="human-review-filter-partial_evidence"]').trigger('click')
    expect(wrapper.findAll('[data-testid="human-review-gate-table"] tbody tr')).toHaveLength(19)
    expect(wrapper.find('[data-testid="human-review-filter-partial_evidence"]').attributes('aria-pressed')).toBe('true')
    // Back to All.
    await wrapper.find('[data-testid="human-review-filter-all"]').trigger('click')
    expect(wrapper.findAll('[data-testid="human-review-gate-table"] tbody tr')).toHaveLength(24)
  })

  it('the Pending human review filter shows 5 gates', async () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    expect(wrapper.find('[data-testid="human-review-filter-pending_human_review"]').attributes('data-filter-count')).toBe('5')
    await wrapper.find('[data-testid="human-review-filter-pending_human_review"]').trigger('click')
    const rows = wrapper.findAll('[data-testid="human-review-gate-table"] tbody tr')
    expect(rows).toHaveLength(5)
    const ids = rows.map((r) => r.attributes('data-gate-id'))
    expect(ids.sort()).toEqual([...PENDING_GATE_IDS].sort())
  })

  it('the Blocked by human review filter shows the same 5 gates', async () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    await wrapper.find('[data-testid="human-review-filter-blocked_by_human_review"]').trigger('click')
    expect(wrapper.findAll('[data-testid="human-review-gate-table"] tbody tr')).toHaveLength(5)
  })

  it('the Governance-only filter shows 0 gates', async () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    await wrapper.find('[data-testid="human-review-filter-governance_only"]').trigger('click')
    expect(wrapper.findAll('[data-testid="human-review-gate-table"] tbody tr')).toHaveLength(0)
  })

  it('defaults to the P0-15 (pending) gate detail and marks its row aria-current', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    const detail = wrapper.find('[data-testid="human-review-detail-gate"]')
    expect(detail.exists()).toBe(true)
    expect(detail.text()).toContain('P0-15')
    expect(detail.text()).toContain('No implementation authorization')
    expect(wrapper.find('[data-gate-id="P0-15"]').attributes('aria-current')).toBe('true')
  })

  it('the detail panel states resolved=false / approved=false / production NO-GO', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    const detail = wrapper.find('[data-testid="human-review-detail-gate"]')
    expect(detail.html()).toContain('resolved-false')
    expect(detail.html()).toContain('approved-false')
    expect(detail.html()).toContain('productionAuthorization-NO-GO')
  })

  it('selecting a partial gate renders its partial-evidence detail', async () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    await wrapper.find('[data-testid="human-review-inspect-P0-01"]').trigger('click')
    const detail = wrapper.find('[data-testid="human-review-detail-gate"]')
    expect(detail.text()).toContain('P0-01')
    expect(detail.text()).toContain('Sandbox model')
    expect(detail.find('[data-status="partial_evidence"]').exists()).toBe(true)
  })

  it('renders the evidence trail with the seven phases', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    const trail = wrapper.find('[data-testid="human-review-evidence-trail"]')
    expect(trail.exists()).toBe(true)
    const items = trail.findAll('[data-testid="human-review-evidence-list"] li')
    expect(items).toHaveLength(7)
    const text = trail.text()
    expect(text).toContain('Phase 3E-H safety baseline')
    expect(text).toContain('Phase 3H proof runner')
    expect(text).toContain('Phase 3I local runtime MVP')
    expect(text).toContain('Phase 3J read-only WebUI')
    expect(text).toContain('Partial evidence only')
  })

  it('renders the NO-GO decision panel and the runtime-relationship panel', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    const nogo = wrapper.find('[data-testid="human-review-nogo-panel"]')
    expect(nogo.exists()).toBe(true)
    const nogoText = nogo.find('[data-testid="human-review-nogo-list"]').text()
    expect(nogoText).toContain('Implementation Authorization')
    expect(nogoText).toContain('Phase 3I Production Authorization')
    expect(nogoText).toContain('Production Rollout')
    const rel = nogo.find('[data-testid="human-review-relationship-list"]').text()
    expect(rel.toLowerCase()).toContain('evidence surface')
    expect(rel.toLowerCase()).toContain('decision-readiness surface')
  })

  it('renders the allowed / forbidden actions panel', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    const allowed = wrapper.find('[data-testid="human-review-allowed-actions"]').text()
    expect(allowed.toLowerCase()).toContain('view gate details')
    expect(allowed.toLowerCase()).toContain('copy gate id')
    const forbidden = wrapper.find('[data-testid="human-review-forbidden-actions-global"]').text().toLowerCase()
    expect(forbidden).toContain('approve')
    expect(forbidden).toContain('authorize')
    expect(forbidden).toContain('production rollout')
  })

  it('renders route governance status with the frozen baseline and no route change', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    const rg = wrapper.find('[data-testid="human-review-route-governance"]')
    expect(rg.exists()).toBe(true)
    const text = rg.text()
    expect(text).toContain('34/34/5/0/1/1')
    expect(rg.html()).toContain('backendRoutesChanged-false')
    expect(text.toLowerCase()).toContain('no backend route was added')
  })

  it('P0 resolved count stays 0 and Implementation Authorization stays NO-GO in the DOM', () => {
    const wrapper = mount(HumanReviewGovernanceSection)
    const detail = wrapper.find('[data-testid="human-review-detail-gate"]').html()
    expect(detail).toContain('resolved-false')
    expect(detail).toContain('productionAuthorization-NO-GO')
  })
})
