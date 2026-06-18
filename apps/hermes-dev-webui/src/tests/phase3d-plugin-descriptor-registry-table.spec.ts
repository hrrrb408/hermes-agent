/**
 * Phase 3D — Plugin Descriptor Registry table tests.
 *
 * Asserts the table renders all descriptors, blocked descriptors are visually
 * marked, capability bindings are surfaced as plain ids, and selecting a row
 * emits the pluginId.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import PluginDescriptorRegistryTable from '@/components/devconsole/PluginDescriptorRegistryTable.vue'
import { PLUGIN_DESCRIPTOR_MANIFEST } from '@/constants/pluginDescriptorRegistryManifest'

describe('PluginDescriptorRegistryTable (Phase 3D)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the table with all descriptors', () => {
    const wrapper = mount(PluginDescriptorRegistryTable, { props: { descriptors: PLUGIN_DESCRIPTOR_MANIFEST } })
    expect(wrapper.find('[data-testid="plugin-descriptor-registry-table"]').exists()).toBe(true)
    // one row per descriptor (header is thead)
    const rows = wrapper.findAll('.plugin-table tbody tr')
    expect(rows.length).toBe(PLUGIN_DESCRIPTOR_MANIFEST.length)
  })

  it('marks blocked descriptors', () => {
    const blocked = PLUGIN_DESCRIPTOR_MANIFEST.filter((d) => d.status === 'blocked')
    const wrapper = mount(PluginDescriptorRegistryTable, { props: { descriptors: PLUGIN_DESCRIPTOR_MANIFEST } })
    const blockedRows = wrapper.findAll('.plugin-row--blocked')
    expect(blockedRows.length).toBe(blocked.length)
  })

  it('surfaces capability bindings as plain ids', () => {
    const wrapper = mount(PluginDescriptorRegistryTable, { props: { descriptors: PLUGIN_DESCRIPTOR_MANIFEST } })
    const text = wrapper.text()
    expect(text).toContain('registry.capability_registry_status')
    expect(text).toContain('capability.forbidden.marketplace')
  })

  it('emits select with the pluginId on detail click', async () => {
    const wrapper = mount(PluginDescriptorRegistryTable, { props: { descriptors: PLUGIN_DESCRIPTOR_MANIFEST } })
    await wrapper.find('.plugin-view-btn').trigger('click')
    const emittedEvents = wrapper.emitted('select')
    expect(emittedEvents).toBeTruthy()
    const emitted = (emittedEvents![0] as unknown[])[0] as string
    expect(PLUGIN_DESCRIPTOR_MANIFEST.some((d) => d.pluginId === emitted)).toBe(true)
  })
})
