/**
 * Phase 3C-H1 — Capability Registry panel / summary / table hardening.
 *
 * Asserts the read-only registry section renders its summary card, the frozen
 * policy flags, the capability table, and the explicit "describes only / does
 * not grant permission" + "no plugin runtime / dynamic loading / remote
 * registry / marketplace" messaging in both the intro and the summary note.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/capabilityRegistry', () => ({
  fetchCapabilityRegistryStatus: vi.fn().mockResolvedValue(null),
}))

import CapabilityRegistrySection from '@/components/devconsole/CapabilityRegistrySection.vue'
import CapabilityRegistrySummary from '@/components/devconsole/CapabilityRegistrySummary.vue'
import CapabilityRegistryTable from '@/components/devconsole/CapabilityRegistryTable.vue'
import { useCapabilityRegistryStore } from '@/stores/capabilityRegistry'
import type { CapabilityRegistrySummary as SummaryType } from '@/types/api/capabilityRegistry'
import { CAPABILITY_REGISTRY_MANIFEST } from '@/constants/capabilityRegistryManifest'

function makeSummary(overrides: Partial<SummaryType> = {}): SummaryType {
  return {
    status: 'enabled',
    registryVersion: 'phase3c-static-v1',
    loaded: true,
    validationPassed: true,
    capabilityCount: 46,
    enabledCount: 26,
    disabledCount: 2,
    blockedCount: 18,
    plannedCount: 0,
    deprecatedCount: 0,
    permissionClassCounts: { READ_ONLY: 18 },
    trustLevelCounts: { BUILTIN_VERIFIED: 26 },
    categoryCounts: { tool: 10 },
    devOnly: true,
    productionAllowed: false,
    dynamicLoadingAllowed: false,
    remoteRegistryAllowed: false,
    marketplaceAllowed: false,
    routeGovernanceExpected: '34/34/5/0/1/1',
    validation: { valid: true, errorCount: 0, warningCount: 0 },
    redactionApplied: true,
    ...overrides,
  } as SummaryType
}

describe('Phase 3C-H1 — registry panel rendering', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders the section, summary, and table', () => {
    const wrapper = mount(CapabilityRegistrySection)
    expect(wrapper.find('[data-testid="capability-registry-section"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="capability-registry-summary"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="capability-registry-table"]').exists()).toBe(true)
  })

  it('shows the describes-only / does-not-grant-permission intro', () => {
    const wrapper = mount(CapabilityRegistrySection)
    const text = wrapper.text()
    expect(text).toContain('describes only')
    expect(text).toContain('does not grant permission')
    expect(text).toContain('No plugin runtime')
    expect(text).toContain('dynamic loading')
    expect(text).toContain('marketplace')
  })

  it('summary note repeats the describes-only invariant', () => {
    const wrapper = mount(CapabilityRegistrySummary, { props: { summary: makeSummary() } })
    const text = wrapper.text()
    expect(text).toContain('does not grant permission')
    expect(text).toContain('No plugin runtime')
    expect(text).toContain('remote registry')
  })

  it('summary renders the five frozen policy flags as yes/no', () => {
    const wrapper = mount(CapabilityRegistrySummary, { props: { summary: makeSummary() } })
    const flags = wrapper.find('[data-testid="capability-frozen-flags"]')
    expect(flags.exists()).toBe(true)
    const text = flags.text()
    expect(text).toContain('Dev-only:')
    expect(text).toContain('Production allowed:')
    expect(text).toContain('Dynamic loading:')
    expect(text).toContain('Remote registry:')
    expect(text).toContain('Marketplace:')
  })

  it('summary surfaces the route-governance baseline', () => {
    const wrapper = mount(CapabilityRegistrySummary, { props: { summary: makeSummary() } })
    expect(wrapper.text()).toContain('34/34/5/0/1/1')
  })

  it('summary surfaces validation passed with zero errors', () => {
    const wrapper = mount(CapabilityRegistrySummary, { props: { summary: makeSummary() } })
    expect(wrapper.text()).toContain('passed')
    expect(wrapper.text()).toContain('0 errors')
  })

  it('table renders capability rows with the detail action', () => {
    const wrapper = mount(CapabilityRegistryTable, { props: { capabilities: CAPABILITY_REGISTRY_MANIFEST } })
    // Every row exposes a Detail button.
    const detailBtns = wrapper.findAll('button.cap-view-btn')
    expect(detailBtns.length).toBe(CAPABILITY_REGISTRY_MANIFEST.length)
  })

  it('table emits select with the capability id', async () => {
    const wrapper = mount(CapabilityRegistryTable, { props: { capabilities: CAPABILITY_REGISTRY_MANIFEST.slice(0, 3) } })
    const firstBtn = wrapper.findAll('button.cap-view-btn')[0]!
    await firstBtn.trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    const emitted = wrapper.emitted('select')![0]!
    expect(emitted).toEqual([CAPABILITY_REGISTRY_MANIFEST[0]!.capabilityId])
  })

  it('section drives the store filters without mutating the registry', () => {
    const store = useCapabilityRegistryStore()
    const wrapper = mount(CapabilityRegistrySection)
    // No enable/disable/promote/delete control exists — only filters.
    expect(wrapper.findAll('select').length).toBe(4)
    expect(wrapper.find('[data-testid="cap-filter-reset"]').exists()).toBe(true)
    // The store still reports the full immutable manifest.
    expect(store.capabilities.length).toBe(46)
  })
})
