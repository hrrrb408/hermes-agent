/**
 * Phase 3J — Runtime Governance read-only panel tests.
 *
 * Asserts the section renders every required region (header banner, summary
 * cards, descriptor table with the six reviewed descriptors, binding detail,
 * P0 panel, side-effect matrix, fixture allowlist, route governance, CLI
 * examples), that the frozen NO-GO / not-authorized / resolved=0 / all-false
 * invariants are visible, and that the only controls are harmless UI-only
 * selects (inspect descriptor / denied-state preview).
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import RuntimeGovernanceSection from '@/components/devconsole/RuntimeGovernanceSection.vue'

const EXPECTED_DESCRIPTOR_IDS = [
  'descriptor.fixture.echo_uppercase',
  'descriptor.fixture.normalize_text',
  'descriptor.fixture.validate_required_keys',
  'descriptor.fixture.count_items',
  'descriptor.fixture.redact_payload',
  'descriptor.fixture.fault',
]

describe('RuntimeGovernanceSection (Phase 3J) — rendering', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the section with title and dev-only / read-only banner', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    expect(wrapper.find('[data-testid="runtime-governance-section"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Runtime Governance')
    const banner = wrapper.find('[data-testid="runtime-boundary-banner"]')
    expect(banner.exists()).toBe(true)
    const text = wrapper.text().toLowerCase()
    expect(text).toContain('dev-only')
    expect(text).toContain('read-only')
    expect(text).toContain('fixture-only')
  })

  it('renders the summary cards with expected counts', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const text = wrapper.text()
    expect(text).toContain('Reviewed descriptors')
    expect(text).toContain('Supported fixture plugins')
    // Six reviewed descriptors, seven fixture allowlist pairs.
    expect(text).toContain('6')
    expect(text).toContain('7')
  })

  it('renders the descriptor table with exactly the six reviewed descriptors', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const table = wrapper.find('[data-testid="runtime-descriptor-table"]')
    expect(table.exists()).toBe(true)
    for (const id of EXPECTED_DESCRIPTOR_IDS) {
      expect(table.find(`[data-descriptor-id="${id}"]`).exists(), id).toBe(true)
    }
    expect(table.findAll('tbody tr')).toHaveLength(6)
  })

  it('marks every descriptor dev-only / fixture-only / reviewed and not executable/remote/marketplace/production/routeChange', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const html = wrapper.find('[data-testid="runtime-descriptor-table"]').html()
    expect(html).toContain('devOnly-true')
    expect(html).toContain('fixtureOnly-true')
    expect(html).toContain('reviewedFixture-true')
    expect(html).toContain('executable-false')
    expect(html).toContain('remote-false')
    expect(html).toContain('marketplace-false')
    expect(html).toContain('production-false')
    expect(html).toContain('routeChange-false')
    expect(html).toContain('bindingAllowed-true')
    // No descriptor is marked executable/remote/marketplace/production true.
    expect(html).not.toContain('executable-true')
    expect(html).not.toContain('remote-true')
    expect(html).not.toContain('marketplace-true')
    expect(html).not.toContain('production-true')
  })

  it('renders the default descriptor binding detail (echo_uppercase)', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const detail = wrapper.find('[data-testid="runtime-detail-binding"]')
    expect(detail.exists()).toBe(true)
    const text = detail.text()
    expect(text).toContain('descriptor.fixture.echo_uppercase')
    expect(text).toContain('fixture.echo')
    expect(text).toContain('echo_uppercase')
    expect(text).toContain('static_descriptor_registry')
    expect(detail.html()).toContain('bindingAllowed-true')
  })

  it('selecting another descriptor updates the read-only binding detail', async () => {
    const wrapper = mount(RuntimeGovernanceSection)
    await wrapper.find('[data-testid="runtime-inspect-descriptor.fixture.redact_payload"]').trigger('click')
    const detail = wrapper.find('[data-testid="runtime-detail-binding"]')
    expect(detail.text()).toContain('descriptor.fixture.redact_payload')
    expect(detail.text()).toContain('fixture.redact')
    expect(detail.text()).toContain('redact_payload')
  })

  it('can preview the denied-binding state and return to the selected binding', async () => {
    const wrapper = mount(RuntimeGovernanceSection)
    await wrapper.find('[data-testid="runtime-denied-preview-toggle"]').trigger('click')
    const denied = wrapper.find('[data-testid="runtime-detail-denied"]')
    expect(denied.exists()).toBe(true)
    expect(denied.text().toLowerCase()).toContain('denied')
    expect(wrapper.find('[data-testid="runtime-detail-denial-reasons"]').text()).toContain(
      'descriptor_not_in_static_registry',
    )
    // Toggle back.
    await wrapper.find('[data-testid="runtime-denied-preview-toggle"]').trigger('click')
    expect(wrapper.find('[data-testid="runtime-detail-binding"]').exists()).toBe(true)
  })

  it('renders the P0 panel with total=24, resolved=0, and frozen NO-GO gates', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const p0 = wrapper.find('[data-testid="runtime-p0-evidence-panel"]')
    expect(p0.exists()).toBe(true)
    expect(p0.find('[data-testid="runtime-p0-total"]').text()).toBe('24')
    expect(p0.find('[data-testid="runtime-p0-resolved"]').text()).toBe('0')
    expect(p0.find('[data-testid="runtime-p0-implementation-gate"]').text()).toBe('NO-GO')
    expect(p0.find('[data-testid="runtime-p0-phase3i-gate"]').text()).toBe('NOT_AUTHORIZED')
    const text = p0.text()
    expect(text).toContain('19') // partial evidence
    expect(text).toContain('5') // pending human review
  })

  it('renders the side-effect matrix with every flag false', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const matrix = wrapper.find('[data-testid="runtime-safety-matrix"]')
    expect(matrix.exists()).toBe(true)
    const items = matrix.findAll('[data-testid="runtime-safety-list"] li')
    expect(items.length).toBeGreaterThanOrEqual(12)
    const html = matrix.html()
    expect(html).not.toContain('data-side-effect="true"')
    // Spot-check a few labels.
    const text = matrix.text().toLowerCase()
    expect(text).toContain('production access')
    expect(text).toContain('external network')
    expect(text).toContain('arbitrary plugin load')
    expect(text).toContain('output file write')
  })

  it('renders the fixture allowlist with seven pairs', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const list = wrapper.find('[data-testid="runtime-fixture-allowlist-list"]')
    expect(list.exists()).toBe(true)
    expect(list.findAll('li')).toHaveLength(7)
    const text = list.text()
    expect(text).toContain('fixture.echo / echo_uppercase')
    expect(text).toContain('fixture.fault / deliberate_failure')
  })

  it('renders route governance status with the frozen baseline and no route change', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const rg = wrapper.find('[data-testid="runtime-route-governance"]')
    expect(rg.exists()).toBe(true)
    const text = rg.text()
    expect(text).toContain('34/34/5/0/1/1')
    expect(rg.html()).toContain('backendRoutesChanged-false')
    expect(text.toLowerCase()).toContain('no backend route was added')
  })

  it('renders the CLI examples as text (list/show/run/batch/audit/p0-report)', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const cli = wrapper.find('[data-testid="runtime-cli-examples"]')
    expect(cli.exists()).toBe(true)
    const text = cli.text()
    expect(text).toContain('hermes dev-runtime list')
    expect(text).toContain('hermes dev-runtime show descriptor.fixture.echo_uppercase')
    expect(text).toContain('hermes dev-runtime run descriptor.fixture.echo_uppercase')
    expect(text).toContain('hermes dev-runtime batch --items')
    expect(text).toContain('hermes dev-runtime audit descriptor.fixture.echo_uppercase')
    expect(text).toContain('hermes dev-runtime p0-report')
  })

  it('renders the frozen authorization verdicts in the boundary banner', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    const verdicts = wrapper.find('[data-testid="runtime-boundary-verdicts"]')
    const text = verdicts.text()
    expect(text).toContain('Implementation Authorization')
    expect(text).toContain('Phase 3I Production Authorization')
    expect(text).toContain('Remote Registry')
    expect(text).toContain('Marketplace')
    expect(text).toContain('Arbitrary Plugin Loading')
  })

  it('includes the plugin-runtime-disabled banner', () => {
    const wrapper = mount(RuntimeGovernanceSection)
    expect(wrapper.find('[data-testid="plugin-runtime-disabled-banner"]').exists()).toBe(true)
  })
})
