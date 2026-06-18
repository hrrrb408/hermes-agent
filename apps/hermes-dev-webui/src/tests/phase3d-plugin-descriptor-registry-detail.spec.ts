/**
 * Phase 3D — Plugin Descriptor detail drawer tests.
 *
 * Asserts the drawer renders the safe record (badges, runtime gates,
 * capability bindings, the "describes only / does not grant permission" notice),
 * that the close button emits close, and that the drawer is absent when no
 * descriptor is selected.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import PluginDescriptorRegistryDetailDrawer from '@/components/devconsole/PluginDescriptorRegistryDetailDrawer.vue'
import { PLUGIN_DESCRIPTOR_MANIFEST } from '@/constants/pluginDescriptorRegistryManifest'

describe('PluginDescriptorRegistryDetailDrawer (Phase 3D)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders nothing when no descriptor is selected', () => {
    const wrapper = mount(PluginDescriptorRegistryDetailDrawer, { props: { descriptor: null } })
    expect(wrapper.find('[data-testid="plugin-descriptor-detail-drawer"]').exists()).toBe(false)
  })

  it('renders the safe record for a descriptor', () => {
    const d = PLUGIN_DESCRIPTOR_MANIFEST.find((x) => x.pluginId === 'plugin.descriptor.registry_status')
    expect(d).toBeTruthy()
    const wrapper = mount(PluginDescriptorRegistryDetailDrawer, { props: { descriptor: d ?? null } })
    expect(wrapper.find('[data-testid="plugin-descriptor-detail-drawer"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Plugin Descriptor Registry Status')
    expect(wrapper.find('[data-testid="plugin-runtime-gates"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="plugin-capability-bindings"]').exists()).toBe(true)
  })

  it('shows the describes-only notice', () => {
    const d = PLUGIN_DESCRIPTOR_MANIFEST[0]
    const wrapper = mount(PluginDescriptorRegistryDetailDrawer, { props: { descriptor: d ?? null } })
    const notice = wrapper.find('[data-testid="plugin-describes-only-notice"]')
    expect(notice.exists()).toBe(true)
    expect(notice.text().toLowerCase()).toContain('does not grant permission')
    expect(notice.text().toLowerCase()).toContain('does not execute a plugin')
  })

  it('emits close on the close button', async () => {
    const d = PLUGIN_DESCRIPTOR_MANIFEST[0]
    const wrapper = mount(PluginDescriptorRegistryDetailDrawer, { props: { descriptor: d ?? null } })
    await wrapper.find('.plugin-drawer__close').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('shows the blocked reason for a blocked descriptor', () => {
    const d = PLUGIN_DESCRIPTOR_MANIFEST.find((x) => x.status === 'blocked')
    expect(d).toBeTruthy()
    const wrapper = mount(PluginDescriptorRegistryDetailDrawer, { props: { descriptor: d ?? null } })
    expect(d?.blockedReason).toBeTruthy()
    expect(wrapper.text()).toContain(d!.blockedReason!)
  })
})
