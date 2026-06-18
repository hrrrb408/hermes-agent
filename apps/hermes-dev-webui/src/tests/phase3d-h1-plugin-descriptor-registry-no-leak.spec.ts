/**
 * Phase 3D-H1 — Plugin Descriptor Registry no-leak HARDENING tests.
 *
 * Stricter no-leak pass: scans the full section HTML, iterates every descriptor
 * (selecting it so the detail drawer renders), and asserts no secret, callable
 * repr, shell command, SQL statement, production path, local plugin path,
 * dynamic import path, external URL, download URL, install command,
 * Authorization header, Bearer token, raw token, or forbidden field NAME ever
 * surfaces in the rendered DOM.
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
  'postInstallHook',
  'preExecutionHook',
]

describe('PluginDescriptorRegistry no-leak HARDENING (Phase 3D-H1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('the full section HTML contains no forbidden token', () => {
    const html = mount(PluginDescriptorRegistrySection).html()
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

  it('no production path / state.db / API key / sk- surfaces', () => {
    const html = mount(PluginDescriptorRegistrySection).html()
    expect(html).not.toContain('/Users/huangruibang/.hermes')
    expect(html).not.toContain('state.db')
    expect(html).not.toContain('OPENAI_API_KEY')
    expect(html).not.toContain('sk-')
  })

  it('no forbidden field name is rendered as data', () => {
    const html = mount(PluginDescriptorRegistrySection).html()
    expect(html).not.toContain('pythonImportPath')
    expect(html).not.toContain('shellCommand')
    expect(html).not.toContain('installCommand')
    expect(html).not.toContain('externalUrl')
    expect(html).not.toContain('downloadUrl')
  })

  it('capability bindings surface as plain ids, never as execution surfaces', () => {
    const html = mount(PluginDescriptorRegistrySection).html()
    expect(html).toContain('registry.capability_registry_status')
    // Forbidden capability ids are *described* (declared blocked), which is allowed.
    expect(html).toContain('capability.forbidden.dynamic_plugin_load')
  })
})
