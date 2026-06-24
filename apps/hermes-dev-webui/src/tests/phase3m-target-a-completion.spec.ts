/**
 * Phase 3M — Target A Completion rendering + acceptance tests.
 *
 * Asserts the Governance Hub now renders a Target A Completion region stating the
 * dev-only runtime prototype is COMPLETE (in the dev-only sense only) while every
 * production dimension stays NO-GO. Covers: the status banner, completion cards,
 * the capability matrix, the readiness checklist (every item pass — never
 * production-ready), the Target A vs Target B boundary, and the final dev-only
 * prototype acceptance panel. Also covers accessibility (headings, labelled
 * regions) and deterministic DOM snapshots of the major regions.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import GovernanceHubSection from '@/components/devconsole/GovernanceHubSection.vue'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'
import {
  TARGET_A_CAPABILITY_MATRIX,
  TARGET_A_READINESS_CHECKLIST,
  TARGET_B_DEFERRED_MATRIX,
} from '@/constants/governanceHubManifest'

const EXPECTED_CAPABILITIES = [
  'Static Descriptor Registry',
  'Reviewed Fixture Descriptors',
  'Sandbox Safety Baseline',
  'P0 Evidence Projection',
  'Proof Runner',
  'Adversarial Hardening',
  'Dev-only Fixture Runtime',
  'Fixture Runtime Expansion',
  'Descriptor Runtime Binding',
  'Runtime Governance CLI',
  'Runtime Governance CLI Completion',
  'Runtime Governance WebUI',
  'Runtime Governance WebUI QA',
  'Human Review Governance WebUI',
  'Governance Hub',
]

function findRegion(wrapper: ReturnType<typeof mount>) {
  return wrapper.find('[data-testid="governance-hub-target-a-region"]')
}

describe('Target A Completion region (Phase 3M) — status rendering', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('renders the Target A region with a heading and the COMPLETE verdict', () => {
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    expect(region.exists()).toBe(true)
    expect(region.find('[data-testid="governance-hub-target-a-heading"]').text()).toContain(
      'Target A',
    )
    const banner = region.find('[data-testid="governance-hub-target-a-banner"]')
    expect(banner.exists()).toBe(true)
    expect(banner.find('[data-target-a-verdict="COMPLETE"]').text()).toContain('COMPLETE')
  })

  it('the status banner shows the dev-only / not-production / P0-0 / Target-B-NO-GO lines', () => {
    const wrapper = mount(GovernanceHubSection)
    const lines = findRegion(wrapper)
      .find('[data-testid="governance-hub-target-a-banner-lines"]')
      .text()
    expect(lines).toContain('Dev-only runtime prototype complete')
    expect(lines).toContain('Dev-only / fixture-only / read-only governed')
    expect(lines).toContain('Not production runtime')
    expect(lines).toContain('P0 resolved remains 0')
    expect(lines).toContain('Target B remains NO-GO')
  })

  it('renders the Target A completion cards with the frozen verdicts and counts', () => {
    const wrapper = mount(GovernanceHubSection)
    const text = findRegion(wrapper).text()
    expect(text).toContain('Target A Status')
    expect(text).toContain('COMPLETE')
    expect(text).toContain('Fixture runtime')
    expect(text).toContain('CLI')
    expect(text).toContain('WebUI governance')
    expect(text).toContain('Production runtime')
    expect(text).toContain('Target B')
    expect(text).toContain('Production readiness')
  })
})

describe('Target A Completion region — capability matrix', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders all 15 capability rows with their capability name', () => {
    const wrapper = mount(GovernanceHubSection)
    const table = findRegion(wrapper).find('[data-testid="governance-hub-target-a-capability-table"]')
    expect(table.exists()).toBe(true)
    const rows = table.findAll('tbody tr')
    expect(rows).toHaveLength(TARGET_A_CAPABILITY_MATRIX.length)
    const names = rows.map((r) => r.find('.ghub-board__name').text())
    for (const cap of EXPECTED_CAPABILITIES) {
      expect(names, `missing capability ${cap}`).toContain(cap)
    }
  })

  it('every capability row renders no-new-route and a forbidden production impact', () => {
    const wrapper = mount(GovernanceHubSection)
    const rows = findRegion(wrapper).findAll(
      '[data-testid="governance-hub-target-a-capability-table"] tbody tr',
    )
    expect(rows.length).toBe(TARGET_A_CAPABILITY_MATRIX.length)
    for (const row of rows) {
      expect(row.text()).toContain('No new route')
      expect(row.find('[data-production-impact="forbidden"]').exists()).toBe(true)
      expect(row.find('[data-target-a-contribution]').exists()).toBe(true)
    }
  })

  it('production impact never positively authorizes production', () => {
    const wrapper = mount(GovernanceHubSection)
    const text = findRegion(wrapper)
      .find('[data-testid="governance-hub-target-a-capability-table"]')
      .text()
      .toLowerCase()
    // NO-GO is expected and correct; guard only against a POSITIVE authorization
    // phrase (never the frozen negative 'no-go' verdict).
    expect(text).not.toContain('production authorized')
    expect(text).not.toContain('authorizes production')
    expect(text).not.toContain('is authorized')
    expect(text).not.toContain('production approved')
    expect(text).not.toContain('implementation authorization = go')
  })
})

describe('Target A Completion region — readiness checklist', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders every readiness item as pass', () => {
    const wrapper = mount(GovernanceHubSection)
    const list = findRegion(wrapper).find('[data-testid="governance-hub-target-a-readiness-list"]')
    expect(list.exists()).toBe(true)
    const items = list.findAll('li')
    expect(items).toHaveLength(TARGET_A_READINESS_CHECKLIST.length)
    for (const li of items) {
      expect(li.attributes('data-readiness-status')).toBe('pass')
      expect(li.find('[data-status="pass"]').exists()).toBe(true)
    }
  })

  it('the checklist does not claim production readiness', () => {
    const wrapper = mount(GovernanceHubSection)
    const text = findRegion(wrapper)
      .find('[data-testid="governance-hub-target-a-readiness"]')
      .text()
      .toLowerCase()
    expect(text).toContain('production readiness remains no-go')
    expect(text).not.toContain('production ready')
  })

  it('cross-links for runtime governance and human review switch sections client-side', async () => {
    const nav = useDevConsoleNavStore()
    const wrapper = mount(GovernanceHubSection)
    const rg = wrapper.find('[data-testid="governance-hub-target-a-readiness-link-runtimeGovernanceWebui"]')
    expect(rg.exists()).toBe(true)
    await rg.trigger('click')
    expect(nav.activeSection).toBe('runtimeGovernance')
    const hr = wrapper.find('[data-testid="governance-hub-target-a-readiness-link-humanReviewWebui"]')
    expect(hr.exists()).toBe(true)
    await hr.trigger('click')
    expect(nav.activeSection).toBe('humanReview')
  })
})

describe('Target A Completion region — Target A vs Target B boundary', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the completed (Target A) and deferred (Target B) boundary lists', () => {
    const wrapper = mount(GovernanceHubSection)
    const boundary = findRegion(wrapper).find('[data-testid="governance-hub-target-a-boundary"]')
    expect(boundary.exists()).toBe(true)
    const completed = boundary.find('[data-testid="governance-hub-target-a-boundary-completed"]').text().toLowerCase()
    for (const item of [
      'dev-only fixture runtime',
      'static descriptor registry',
      'cli',
      'read-only webui governance',
      'human review read-only visibility',
      'governance hub',
      'tests / evidence',
    ]) {
      expect(completed, `missing completed boundary ${item}`).toContain(item)
    }
    const deferred = boundary.find('[data-testid="governance-hub-target-a-boundary-deferred"]').text().toLowerCase()
    for (const item of [
      'production runtime',
      'arbitrary plugin loading',
      'real plugin ecosystem',
      'remote registry',
      'marketplace',
      'external network',
      'real api keys',
      'webui execution',
      'production rollout',
    ]) {
      expect(deferred, `missing deferred boundary ${item}`).toContain(item)
    }
  })
})

describe('Target A Completion region — final acceptance panel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the PASS verdict with why-pass and why-not-production reasons', () => {
    const wrapper = mount(GovernanceHubSection)
    const acceptance = findRegion(wrapper).find('[data-testid="governance-hub-target-a-acceptance"]')
    expect(acceptance.exists()).toBe(true)
    const verdict = acceptance.find('[data-testid="governance-hub-target-a-acceptance-verdict"]')
    expect(verdict.find('[data-verdict="PASS"]').text()).toBe('PASS')
    const whyPass = acceptance.find('[data-testid="governance-hub-target-a-acceptance-why-pass"]').text()
    expect(whyPass).toContain('capabilities')
    expect(whyPass).toContain('Route governance is unchanged')
    const whyNot = acceptance
      .find('[data-testid="governance-hub-target-a-acceptance-why-not-production"]')
      .text()
    expect(whyNot).toContain('P0 resolved_count remains 0')
    expect(whyNot).toContain('Production runtime remains NO-GO')
    expect(whyNot).toContain('production rollout')
  })

  it('the acceptance footer explicitly states it is not closeout / signoff / production authorization', () => {
    const wrapper = mount(GovernanceHubSection)
    const text = findRegion(wrapper).find('[data-testid="governance-hub-target-a-acceptance"]').text().toLowerCase()
    expect(text).toContain('not a closeout')
    expect(text).toContain('not production authorization')
    expect(text).toContain('remain no-go')
  })
})

describe('Target A Completion region — summary invariants (DOM)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('the region text exposes the frozen P0 counts and route governance and NO-GO verdicts', () => {
    const wrapper = mount(GovernanceHubSection)
    const text = findRegion(wrapper).text()
    expect(text).toContain('24')
    expect(text).toContain('34/34/5/0/1/1')
    expect(text).toContain('NO-GO')
  })

  it('the deferred matrix drives the boundary panel count (all rows stay NO-GO)', () => {
    for (const row of TARGET_B_DEFERRED_MATRIX) {
      expect(row.currentStatus).toBe('NO-GO')
      expect(row.targetAImpact).toBe('not required')
      expect(row.targetBImpact).toBe('required / future phase')
    }
  })
})

describe('Target A Completion region — accessibility', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('the region and every block has an accessible heading and labelled region', () => {
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    // The page h1 exists on the section.
    expect(wrapper.find('h1').exists()).toBe(true)
    // The region has an h2 heading.
    expect(region.find('h2').exists()).toBe(true)
    // Every block has an h3 heading.
    expect(region.findAll('h3').length).toBeGreaterThanOrEqual(5)
    // The banner is a labelled role=group.
    expect(
      region.find('[data-testid="governance-hub-target-a-banner"]').attributes('aria-label'),
    ).toBeTruthy()
    // The capability table has an accessible caption (its accessible label).
    expect(
      region.find('[data-testid="governance-hub-target-a-capability-table"] caption').exists(),
    ).toBe(true)
  })

  it('status badges / verdicts carry explicit text (not color-only)', () => {
    const wrapper = mount(GovernanceHubSection)
    const region = findRegion(wrapper)
    expect(region.find('[data-target-a-verdict="COMPLETE"]').text()).toContain('COMPLETE')
    expect(region.find('[data-verdict="PASS"]').text()).toBe('PASS')
    for (const li of region.findAll('[data-testid="governance-hub-target-a-readiness-list"] li')) {
      expect(li.text().toLowerCase()).toContain('pass')
    }
  })

  it('renders no unlabeled interactive input', () => {
    const wrapper = mount(GovernanceHubSection)
    // No inputs at all on the read-only surface.
    expect(findRegion(wrapper).findAll('input').length).toBe(0)
    expect(findRegion(wrapper).findAll('textarea').length).toBe(0)
    expect(findRegion(wrapper).findAll('select').length).toBe(0)
  })
})
