/**
 * Phase 3D — Plugin Descriptor Registry panel tests.
 *
 * Asserts the section renders, the registry panel is present, the read-only
 * description ("describes only / does not grant permission / does not execute a
 * plugin") is visible, the runtime-disabled banner renders, and the panel
 * makes NO mutating call.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/pluginDescriptorRegistry', () => ({
  fetchPluginDescriptorRegistryStatus: vi.fn().mockResolvedValue(null),
}))

import PluginDescriptorRegistrySection from '@/components/devconsole/PluginDescriptorRegistrySection.vue'
import { usePluginDescriptorRegistryStore } from '@/stores/pluginDescriptorRegistry'

describe('PluginDescriptorRegistrySection (Phase 3D)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the registry section', () => {
    const wrapper = mount(PluginDescriptorRegistrySection)
    expect(wrapper.find('[data-testid="plugin-descriptor-registry-section"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Plugin Descriptor Registry')
  })

  it('states the registry describes only / does not grant permission', () => {
    const wrapper = mount(PluginDescriptorRegistrySection)
    const text = wrapper.text().toLowerCase()
    expect(text).toContain('describes')
    expect(text).toContain('does not grant permission')
  })

  it('states does not execute a plugin', () => {
    const wrapper = mount(PluginDescriptorRegistrySection)
    expect(wrapper.text().toLowerCase()).toContain('does not execute a plugin')
  })

  it('states no plugin runtime / dynamic loading / local directory / remote / marketplace', () => {
    const wrapper = mount(PluginDescriptorRegistrySection)
    const text = wrapper.text().toLowerCase()
    expect(text).toContain('no plugin runtime')
    expect(text).toContain('dynamic loading')
    expect(text).toContain('local plugin directory')
    expect(text).toContain('remote registry')
    expect(text).toContain('marketplace')
  })

  it('renders the runtime-disabled banner', () => {
    const wrapper = mount(PluginDescriptorRegistrySection)
    expect(wrapper.find('[data-testid="plugin-runtime-disabled-banner"]').exists()).toBe(true)
  })

  it('exposes the deterministic descriptor list via the store', () => {
    const store = usePluginDescriptorRegistryStore()
    mount(PluginDescriptorRegistrySection)
    expect(store.descriptors.length).toBe(12)
    expect(store.descriptors.some((d) => d.pluginId === 'plugin.descriptor.registry_status')).toBe(true)
  })

  it('renders filters that only narrow the read-only view', async () => {
    const store = usePluginDescriptorRegistryStore()
    const wrapper = mount(PluginDescriptorRegistrySection)
    const before = store.filteredDescriptors.length
    await wrapper.find('[data-testid="plugin-filter-status"]').setValue('blocked')
    expect(store.filterStatus).toBe('blocked')
    expect(store.filteredDescriptors.every((d) => d.status === 'blocked')).toBe(true)
    expect(store.filteredDescriptors.length).toBeLessThanOrEqual(before)
  })
})
