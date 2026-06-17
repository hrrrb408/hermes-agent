/**
 * Phase 3C — Capability Registry no-leak tests.
 *
 * Asserts the rendered registry UI never surfaces a secret, callable repr,
 * shell command, SQL statement, production path, local plugin path, dynamic
 * import path, external URL, Authorization header, Bearer token, or raw token.
 * Scans the full section (summary + table + drawer) text.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/capabilityRegistry', () => ({
  fetchCapabilityRegistryStatus: vi.fn().mockResolvedValue(null),
}))

import CapabilityRegistrySection from '@/components/devconsole/CapabilityRegistrySection.vue'
import { useCapabilityRegistryStore } from '@/stores/capabilityRegistry'
import { CAPABILITY_REGISTRY_MANIFEST } from '@/constants/capabilityRegistryManifest'

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
]

describe('CapabilityRegistry no-leak (Phase 3C)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('the section rendered text contains no forbidden token', () => {
    const wrapper = mount(CapabilityRegistrySection)
    const html = wrapper.html()
    for (const token of FORBIDDEN_TOKENS) {
      expect(html).not.toContain(token)
    }
  })

  it('selecting every capability and rendering its detail leaks nothing', async () => {
    const store = useCapabilityRegistryStore()
    const wrapper = mount(CapabilityRegistrySection)
    for (const cap of CAPABILITY_REGISTRY_MANIFEST) {
      store.selectCapability(cap.capabilityId)
      await wrapper.vm.$nextTick()
      const html = wrapper.html()
      for (const token of FORBIDDEN_TOKENS) {
        if (html.includes(token)) {
          throw new Error(`forbidden token ${token} leaked for ${cap.capabilityId}`)
        }
      }
    }
    // sanity: at least one capability was checked
    expect(CAPABILITY_REGISTRY_MANIFEST.length).toBeGreaterThan(20)
  })

  it('no production path or state.db surfaces', () => {
    const wrapper = mount(CapabilityRegistrySection)
    const html = wrapper.html()
    expect(html).not.toContain('/Users/huangruibang/.hermes')
    expect(html).not.toContain('state.db')
  })

  it('no forbidden field name is rendered as data', () => {
    const wrapper = mount(CapabilityRegistrySection)
    // The forbidden-field constant names live in source, not in rendered output.
    expect(wrapper.html()).not.toContain('pythonImportPath')
    expect(wrapper.html()).not.toContain('shellCommand')
  })
})
