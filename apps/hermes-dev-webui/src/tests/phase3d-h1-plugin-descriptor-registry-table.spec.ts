/**
 * Phase 3D-H1 — Plugin Descriptor Registry table HARDENING tests.
 *
 * Re-asserts the table renders all 12 descriptors, partitions them into the
 * visible / disabled / blocked groups, marks blocked rows, surfaces capability
 * bindings as plain ids, emits select on detail click, and leaks no forbidden
 * token. Handles the empty state gracefully.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import PluginDescriptorRegistryTable from '@/components/devconsole/PluginDescriptorRegistryTable.vue'
import { PLUGIN_DESCRIPTOR_MANIFEST } from '@/constants/pluginDescriptorRegistryManifest'

const FORBIDDEN_TOKENS = [
  'apiKey',
  'Authorization',
  'Bearer',
  'shellCommand',
  'pythonImportPath',
  'externalUrl',
  'downloadUrl',
  'productionPath',
  'callable',
  'secret',
  'installCommand',
  'localPath',
  'remoteUrl',
]

describe('PluginDescriptorRegistryTable HARDENING (Phase 3D-H1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders one row per descriptor (12 total)', () => {
    const wrapper = mount(PluginDescriptorRegistryTable, {
      props: { descriptors: PLUGIN_DESCRIPTOR_MANIFEST },
    })
    expect(wrapper.find('[data-testid="plugin-descriptor-registry-table"]').exists()).toBe(true)
    const rows = wrapper.findAll('.plugin-table tbody tr')
    expect(rows.length).toBe(12)
  })

  it('partitions descriptors into visible / disabled / blocked', () => {
    const wrapper = mount(PluginDescriptorRegistryTable, {
      props: { descriptors: PLUGIN_DESCRIPTOR_MANIFEST },
    })
    const visible = PLUGIN_DESCRIPTOR_MANIFEST.filter((d) => d.status === 'visible').length
    const disabled = PLUGIN_DESCRIPTOR_MANIFEST.filter((d) => d.status === 'disabled').length
    const blocked = PLUGIN_DESCRIPTOR_MANIFEST.filter((d) => d.status === 'blocked').length
    expect(visible).toBe(3)
    expect(disabled).toBe(4)
    expect(blocked).toBe(5)
    expect(wrapper.findAll('.plugin-row--blocked').length).toBe(blocked)
  })

  it('surfaces capability bindings as plain ids (registry + forbidden)', () => {
    const text = mount(PluginDescriptorRegistryTable, {
      props: { descriptors: PLUGIN_DESCRIPTOR_MANIFEST },
    }).text()
    expect(text).toContain('registry.capability_registry_status')
    expect(text).toContain('capability.forbidden.marketplace')
    expect(text).toContain('capability.forbidden.production_operation')
  })

  it('emits select with a valid pluginId on detail click', async () => {
    const wrapper = mount(PluginDescriptorRegistryTable, {
      props: { descriptors: PLUGIN_DESCRIPTOR_MANIFEST },
    })
    await wrapper.find('.plugin-view-btn').trigger('click')
    const emitted = wrapper.emitted('select')
    expect(emitted).toBeTruthy()
    const pid = (emitted![0] as unknown[])[0] as string
    expect(PLUGIN_DESCRIPTOR_MANIFEST.some((d) => d.pluginId === pid)).toBe(true)
  })

  it('the rendered table leaks no forbidden token', () => {
    const html = mount(PluginDescriptorRegistryTable, {
      props: { descriptors: PLUGIN_DESCRIPTOR_MANIFEST },
    }).html()
    for (const token of FORBIDDEN_TOKENS) {
      expect(html, `forbidden token ${token}`).not.toContain(token)
    }
    expect(html).not.toContain('/Users/huangruibang/.hermes')
    expect(html).not.toContain('state.db')
  })

  it('handles the empty state gracefully', () => {
    const wrapper = mount(PluginDescriptorRegistryTable, { props: { descriptors: [] } })
    expect(wrapper.find('[data-testid="plugin-descriptor-registry-table"]').exists()).toBe(true)
    expect(wrapper.findAll('.plugin-table tbody tr').length).toBe(0)
  })
})
