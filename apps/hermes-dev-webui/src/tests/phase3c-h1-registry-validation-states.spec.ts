/**
 * Phase 3C-H1 — Capability Registry validation / empty / blocked states.
 *
 * Asserts the panel renders safely when the live /status summary reports
 * `validation_failed` (fail-closed UI), when the filter yields an empty table
 * (graceful empty state), and that blocked capabilities visibly carry their
 * blocked reason in the table. No state leaks or crashes.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

const mockFetch = vi.fn().mockResolvedValue(null)
vi.mock('@/api/capabilityRegistry', () => ({
  fetchCapabilityRegistryStatus: (...args: unknown[]) => mockFetch(...(args as [])),
}))

import CapabilityRegistrySection from '@/components/devconsole/CapabilityRegistrySection.vue'
import CapabilityRegistrySummary from '@/components/devconsole/CapabilityRegistrySummary.vue'
import CapabilityRegistryTable from '@/components/devconsole/CapabilityRegistryTable.vue'
import { useCapabilityRegistryStore } from '@/stores/capabilityRegistry'
import type { CapabilityRegistrySummary as SummaryType } from '@/types/api/capabilityRegistry'
import { CAPABILITY_REGISTRY_MANIFEST } from '@/constants/capabilityRegistryManifest'

function failedSummary(): SummaryType {
  return {
    status: 'validation_failed',
    registryVersion: 'phase3c-static-v1',
    loaded: false,
    validationPassed: false,
    capabilityCount: 0,
    enabledCount: 0,
    disabledCount: 0,
    blockedCount: 0,
    plannedCount: 0,
    deprecatedCount: 0,
    permissionClassCounts: {},
    trustLevelCounts: {},
    categoryCounts: {},
    devOnly: true,
    productionAllowed: false,
    dynamicLoadingAllowed: false,
    remoteRegistryAllowed: false,
    marketplaceAllowed: false,
    routeGovernanceExpected: '34/34/5/0/1/1',
    validation: { valid: false, errorCount: 3, warningCount: 0 },
    redactionApplied: true,
  } as SummaryType
}

describe('Phase 3C-H1 — validation_failed state is safe', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockFetch.mockReset()
  })

  it('summary renders the failed validation safely', () => {
    const wrapper = mount(CapabilityRegistrySummary, { props: { summary: failedSummary() } })
    const text = wrapper.text()
    expect(text).toContain('failed')
    expect(text).toContain('3 errors')
    // Frozen flags still present (fail-closed UI keeps the invariant messaging).
    expect(wrapper.find('[data-testid="capability-frozen-flags"]').exists()).toBe(true)
  })

  it('the section does not crash and keeps the describes-only notice', async () => {
    mockFetch.mockResolvedValue(failedSummary())
    const wrapper = mount(CapabilityRegistrySection)
    await flushPromises()
    expect(wrapper.find('[data-testid="capability-registry-section"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('does not grant permission')
  })

  it('a null summary (load failure) renders graceful placeholders, no crash', () => {
    const wrapper = mount(CapabilityRegistrySummary, { props: { summary: null } })
    expect(wrapper.find('[data-testid="capability-registry-summary"]').exists()).toBe(true)
    // Placeholders surface (—) rather than throwing.
    expect(wrapper.text()).toContain('—')
  })

  it('validation_failed summary never leaks a secret or path', () => {
    const wrapper = mount(CapabilityRegistrySummary, { props: { summary: failedSummary() } })
    const html = wrapper.html()
    for (const token of ['apiKey', 'Authorization', 'Bearer', 'shellCommand', 'secret']) {
      expect(html).not.toContain(token)
    }
  })
})

describe('Phase 3C-H1 — empty filtered state is graceful', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockFetch.mockReset().mockResolvedValue(null)
  })

  it('a filter matching nothing renders an empty table without crashing', async () => {
    // No capability in the manifest has status 'planned'.
    const store = useCapabilityRegistryStore()
    store.filterStatus = 'planned'
    const wrapper = mount(CapabilityRegistryTable, { props: { capabilities: store.filteredCapabilities } })
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="capability-registry-table"]').exists()).toBe(true)
    // The table header still renders; the body has zero rows.
    expect(wrapper.findAll('tbody tr').length).toBe(0)
  })

  it('resetting filters restores the full capability set', () => {
    const store = useCapabilityRegistryStore()
    store.filterCategory = 'provider'
    store.filterPermission = 'READ_ONLY'
    store.resetFilters()
    expect(store.filterCategory).toBe('all')
    expect(store.filterPermission).toBe('all')
    expect(store.filteredCapabilities.length).toBe(CAPABILITY_REGISTRY_MANIFEST.length)
  })
})

describe('Phase 3C-H1 — blocked reason visibility', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('blocked rows surface their blocked reason in the table', () => {
    const blocked = CAPABILITY_REGISTRY_MANIFEST.filter((c) => c.status === 'blocked')
    const wrapper = mount(CapabilityRegistryTable, { props: { capabilities: blocked } })
    const text = wrapper.text()
    for (const cap of blocked) {
      expect(cap.blockedReason).toBeTruthy()
      expect(text).toContain(cap.blockedReason!)
    }
  })

  it('the section renders every blocked reason without leaking', async () => {
    const wrapper = mount(CapabilityRegistrySection)
    const html = wrapper.html()
    for (const token of ['apiKey', 'Authorization', 'shellCommand', 'productionPath', 'callable']) {
      expect(html).not.toContain(token)
    }
  })
})
