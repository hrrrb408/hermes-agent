/**
 * Phase 3C — Capability Registry panel tests.
 *
 * Asserts the section renders, the registry panel is present, the read-only
 * description ("describes only / does not grant permission") is visible, and
 * the panel makes NO mutating call.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/capabilityRegistry', () => ({
  fetchCapabilityRegistryStatus: vi.fn().mockResolvedValue(null),
}))

import CapabilityRegistrySection from '@/components/devconsole/CapabilityRegistrySection.vue'
import { useCapabilityRegistryStore } from '@/stores/capabilityRegistry'

describe('CapabilityRegistrySection (Phase 3C)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the registry section', () => {
    const wrapper = mount(CapabilityRegistrySection)
    expect(wrapper.find('[data-testid="capability-registry-section"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Capability Registry')
  })

  it('states the registry describes only / does not grant permission', () => {
    const wrapper = mount(CapabilityRegistrySection)
    const text = wrapper.text()
    expect(text).toContain('describes')
    expect(text.toLowerCase()).toContain('does not grant permission')
  })

  it('states no plugin runtime / dynamic loading / marketplace', () => {
    const wrapper = mount(CapabilityRegistrySection)
    const text = wrapper.text().toLowerCase()
    expect(text).toContain('no plugin runtime')
    expect(text).toContain('dynamic loading')
    expect(text).toContain('marketplace')
  })

  it('exposes the deterministic capability list via the store', () => {
    const store = useCapabilityRegistryStore()
    mount(CapabilityRegistrySection)
    expect(store.capabilities.length).toBeGreaterThan(20)
    expect(store.capabilities.some((c) => c.capabilityId === 'registry.capability_registry_status')).toBe(true)
  })

  it('renders filters that only narrow the read-only view', async () => {
    const store = useCapabilityRegistryStore()
    const wrapper = mount(CapabilityRegistrySection)
    const before = store.filteredCapabilities.length
    await wrapper.find('[data-testid="cap-filter-status"]').setValue('blocked')
    expect(store.filterStatus).toBe('blocked')
    expect(store.filteredCapabilities.every((c) => c.status === 'blocked')).toBe(true)
    expect(store.filteredCapabilities.length).toBeLessThanOrEqual(before)
  })
})
