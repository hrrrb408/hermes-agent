/**
 * Phase 3D-H1 — Plugin Descriptor detail drawer HARDENING tests.
 *
 * Re-asserts the drawer renders the safe record for every descriptor (runtime
 * gates + capability bindings + describes-only notice), shows blocked reasons,
 * emits close, and that selecting every descriptor and rendering its detail
 * leaks no forbidden token.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import PluginDescriptorRegistryDetailDrawer from '@/components/devconsole/PluginDescriptorRegistryDetailDrawer.vue'
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

describe('PluginDescriptorRegistryDetailDrawer HARDENING (Phase 3D-H1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders nothing when no descriptor is selected', () => {
    const wrapper = mount(PluginDescriptorRegistryDetailDrawer, { props: { descriptor: null } })
    expect(wrapper.find('[data-testid="plugin-descriptor-detail-drawer"]').exists()).toBe(false)
  })

  it('renders the safe record (gates + bindings + notice) for every descriptor', () => {
    for (const d of PLUGIN_DESCRIPTOR_MANIFEST) {
      const wrapper = mount(PluginDescriptorRegistryDetailDrawer, { props: { descriptor: d } })
      expect(wrapper.find('[data-testid="plugin-descriptor-detail-drawer"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="plugin-runtime-gates"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="plugin-capability-bindings"]').exists()).toBe(true)
      const notice = wrapper.find('[data-testid="plugin-describes-only-notice"]')
      expect(notice.exists()).toBe(true)
      expect(notice.text().toLowerCase()).toContain('does not grant permission')
      expect(notice.text().toLowerCase()).toContain('does not execute a plugin')
    }
  })

  it('shows the blocked reason for every blocked descriptor', () => {
    for (const d of PLUGIN_DESCRIPTOR_MANIFEST.filter((x) => x.status === 'blocked')) {
      const wrapper = mount(PluginDescriptorRegistryDetailDrawer, { props: { descriptor: d } })
      expect(d.blockedReason).toBeTruthy()
      expect(wrapper.text()).toContain(d.blockedReason!)
    }
  })

  it('emits close on the close button', async () => {
    const wrapper = mount(PluginDescriptorRegistryDetailDrawer, {
      props: { descriptor: PLUGIN_DESCRIPTOR_MANIFEST[0] ?? null },
    })
    await wrapper.find('.plugin-drawer__close').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('rendering every descriptor detail leaks no forbidden token', () => {
    for (const d of PLUGIN_DESCRIPTOR_MANIFEST) {
      const html = mount(PluginDescriptorRegistryDetailDrawer, { props: { descriptor: d } }).html()
      for (const token of FORBIDDEN_TOKENS) {
        if (html.includes(token)) {
          throw new Error(`forbidden token ${token} leaked for ${d.pluginId}`)
        }
      }
      expect(html).not.toContain('/Users/huangruibang/.hermes')
      expect(html).not.toContain('state.db')
    }
  })

  it('every descriptor is dev-only / production-not-allowed / disabled-by-default in the gate list', () => {
    for (const d of PLUGIN_DESCRIPTOR_MANIFEST) {
      expect(d.devOnly).toBe(true)
      expect(d.productionAllowed).toBe(false)
      expect(d.disabledByDefault).toBe(true)
    }
  })
})
