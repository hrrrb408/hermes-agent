/**
 * Phase 3D — Plugin Descriptor Registry no-leak tests.
 *
 * Asserts the rendered registry UI never surfaces a secret, callable repr,
 * shell command, SQL statement, production path, local plugin path, dynamic
 * import path, external URL, download URL, install command, Authorization
 * header, Bearer token, or raw token. Scans the full section (banner + summary
 * + table + every detail drawer) text.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/pluginDescriptorRegistry', () => ({
  fetchPluginDescriptorRegistryStatus: vi.fn().mockResolvedValue(null),
}))

import PluginDescriptorRegistrySection from '@/components/devconsole/PluginDescriptorRegistrySection.vue'
import { usePluginDescriptorRegistryStore } from '@/stores/pluginDescriptorRegistry'
import { PLUGIN_DESCRIPTOR_MANIFEST } from '@/constants/pluginDescriptorRegistryManifest'

const FORBIDDEN_TOKENS = [
  'apiKey',
  'Authorization',
  'Bearer',
  'shellCommand',
  'pythonImportPath',
  'externalUrl',
  'downloadUrl',
  'pluginPackage',
  'dynamicModule',
  'evalCode',
  'execCode',
  'sqlStatement',
  'productionPath',
  'callable',
  'secret',
  'installCommand',
  'localPath',
  'remoteUrl',
  'bearer',
  'api_key',
  'accessToken',
]

describe('PluginDescriptorRegistry no-leak (Phase 3D)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('the section rendered text contains no forbidden token', () => {
    const wrapper = mount(PluginDescriptorRegistrySection)
    const html = wrapper.html()
    for (const token of FORBIDDEN_TOKENS) {
      expect(html, `forbidden token ${token}`).not.toContain(token)
    }
  })

  it('selecting every descriptor and rendering its detail leaks nothing', async () => {
    const store = usePluginDescriptorRegistryStore()
    const wrapper = mount(PluginDescriptorRegistrySection)
    for (const d of PLUGIN_DESCRIPTOR_MANIFEST) {
      store.selectPlugin(d.pluginId)
      await wrapper.vm.$nextTick()
      const html = wrapper.html()
      for (const token of FORBIDDEN_TOKENS) {
        if (html.includes(token)) {
          throw new Error(`forbidden token ${token} leaked for ${d.pluginId}`)
        }
      }
    }
    expect(PLUGIN_DESCRIPTOR_MANIFEST.length).toBe(12)
  })

  it('no production path or state.db surfaces', () => {
    const wrapper = mount(PluginDescriptorRegistrySection)
    const html = wrapper.html()
    expect(html).not.toContain('/Users/huangruibang/.hermes')
    expect(html).not.toContain('state.db')
    expect(html).not.toContain('OPENAI_API_KEY')
    expect(html).not.toContain('sk-')
  })

  it('no forbidden field name is rendered as data', () => {
    const wrapper = mount(PluginDescriptorRegistrySection)
    const html = wrapper.html()
    expect(html).not.toContain('pythonImportPath')
    expect(html).not.toContain('shellCommand')
    expect(html).not.toContain('installCommand')
  })
})
