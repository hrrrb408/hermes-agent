/**
 * Phase 3D-H1 — Plugin Descriptor Registry panel HARDENING tests.
 *
 * Re-asserts the panel-level boundary invariants: the section renders, states
 * the registry is descriptor-only (does not grant permission / does not execute
 * a plugin / disabled by default), surfaces every frozen disabled flag, renders
 * the runtime-disabled banner, and the rendered HTML leaks no forbidden token.
 * The panel makes no mutating call.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/pluginDescriptorRegistry', () => ({
  fetchPluginDescriptorRegistryStatus: vi.fn().mockResolvedValue(null),
}))

import PluginDescriptorRegistrySection from '@/components/devconsole/PluginDescriptorRegistrySection.vue'
import { usePluginDescriptorRegistryStore } from '@/stores/pluginDescriptorRegistry'

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

describe('PluginDescriptorRegistrySection HARDENING (Phase 3D-H1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the registry section with a stable test id', () => {
    const wrapper = mount(PluginDescriptorRegistrySection)
    expect(wrapper.find('[data-testid="plugin-descriptor-registry-section"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Plugin Descriptor Registry')
  })

  it('states descriptor-only / does not grant permission / does not execute', () => {
    const text = mount(PluginDescriptorRegistrySection).text().toLowerCase()
    expect(text).toContain('descriptor')
    expect(text).toContain('does not grant permission')
    expect(text).toContain('does not execute a plugin')
    expect(text).toContain('disabled by default')
  })

  it('states every frozen disabled boundary as text', () => {
    const text = mount(PluginDescriptorRegistrySection).text().toLowerCase()
    expect(text).toContain('no plugin runtime')
    expect(text).toContain('plugin loader not implemented')
    expect(text).toContain('dynamic loading disabled')
    expect(text).toContain('local plugin directory loading disabled')
    expect(text).toContain('remote registry disabled')
    expect(text).toContain('marketplace disabled')
    expect(text).toContain('external plugin fetch disabled')
    expect(text).toContain('no provider-generated plugin')
    expect(text).toContain('no llm-generated plugin install')
  })

  it('renders the runtime-disabled banner', () => {
    const wrapper = mount(PluginDescriptorRegistrySection)
    expect(wrapper.find('[data-testid="plugin-runtime-disabled-banner"]').exists()).toBe(true)
  })

  it('exposes exactly 12 deterministic descriptors via the store', () => {
    const store = usePluginDescriptorRegistryStore()
    mount(PluginDescriptorRegistrySection)
    expect(store.descriptors.length).toBe(12)
    expect(store.descriptors[0]?.pluginId).toBe('plugin.descriptor.registry_status')
    expect(store.descriptors[11]?.pluginId).toBe('plugin.descriptor.production_operation_blocked')
  })

  it('the rendered HTML leaks no forbidden token', () => {
    const html = mount(PluginDescriptorRegistrySection).html()
    for (const token of FORBIDDEN_TOKENS) {
      expect(html, `forbidden token ${token}`).not.toContain(token)
    }
    expect(html).not.toContain('/Users/huangruibang/.hermes')
    expect(html).not.toContain('state.db')
    expect(html).not.toContain('OPENAI_API_KEY')
    expect(html).not.toContain('sk-')
  })

  it('makes no mutating call on mount', () => {
    const store = usePluginDescriptorRegistryStore()
    mount(PluginDescriptorRegistrySection)
    // The store exposes a read-only descriptor list; no plugin is installed / enabled.
    expect(store.descriptors.every((d) => d.disabledByDefault === true)).toBe(true)
    expect(store.descriptors.every((d) => d.productionAllowed === false)).toBe(true)
  })
})
