/**
 * Phase 3C-H1 — Capability Registry no-leak hardening (frontend).
 *
 * Deepens the Phase 3C no-leak closure: the rendered section (intro + summary
 * + table + every detail drawer), the store state, and the static manifest
 * JSON never surface an API key, Authorization header, Bearer token, callable
 * repr, shell command, SQL statement, production path, local plugin path,
 * dynamic import path, or external URL. No API-key input exists in any state.
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

// Forbidden-field / value tokens. The HTML set avoids very short substrings
// (e.g. bare "sk-") that collide with rendered SVG icon class names such as
// `lucide-flask-conical-icon`; the stricter key-shaped patterns are applied
// to the pure data (store state + manifest JSON) where no SVG noise exists.
const FORBIDDEN_HTML_TOKENS = [
  'apiKey', 'Authorization', 'Bearer', 'shellCommand', 'pythonImportPath',
  'externalUrl', 'downloadUrl', 'pluginPackage', 'dynamicModule', 'evalCode',
  'execCode', 'sqlStatement', 'productionPath', 'callable', 'secret',
]

const FORBIDDEN_DATA_TOKENS = [...FORBIDDEN_HTML_TOKENS, 'sk-', 'BEGIN PRIVATE KEY']

describe('Phase 3C-H1 — registry no-leak (frontend)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('the full section HTML contains no forbidden token', () => {
    const wrapper = mount(CapabilityRegistrySection)
    const html = wrapper.html()
    for (const token of FORBIDDEN_HTML_TOKENS) {
      expect(html, `forbidden token ${token}`).not.toContain(token)
    }
  })

  it('no API-key / password input exists in the section', () => {
    const wrapper = mount(CapabilityRegistrySection)
    expect(wrapper.findAll('input[type="password"]').length).toBe(0)
    expect(wrapper.findAll('input').length).toBe(0)
    expect(wrapper.html().toLowerCase()).not.toMatch(/api ?key/)
  })

  it('the store state never carries a forbidden token', () => {
    setActivePinia(createPinia())
    const store = useCapabilityRegistryStore()
    const blob = JSON.stringify({
      summary: store.summary,
      capabilities: store.capabilities,
      liveSummary: store.liveSummary,
    })
    for (const token of FORBIDDEN_DATA_TOKENS) {
      expect(blob, `forbidden token ${token} in store`).not.toContain(token)
    }
  })

  it('the static manifest JSON never carries a forbidden token', () => {
    const blob = JSON.stringify(CAPABILITY_REGISTRY_MANIFEST)
    for (const token of FORBIDDEN_DATA_TOKENS) {
      expect(blob, `forbidden token ${token} in manifest`).not.toContain(token)
    }
  })

  it('no production path or state.db surfaces anywhere', () => {
    const wrapper = mount(CapabilityRegistrySection)
    const html = wrapper.html()
    expect(html).not.toContain('/Users/huangruibang/.hermes')
    expect(html).not.toContain('state.db')
    expect(JSON.stringify(CAPABILITY_REGISTRY_MANIFEST)).not.toContain('/Users/huangruibang/.hermes')
  })

  it('no forbidden field name is rendered as data across all filters', async () => {
    const store = useCapabilityRegistryStore()
    const wrapper = mount(CapabilityRegistrySection)
    // Exercise every category filter and re-scan.
    for (const cat of ['all', 'tool', 'provider', 'workflow', 'sandbox', 'audit', 'registry', 'system'] as const) {
      store.filterCategory = cat
      await wrapper.vm.$nextTick()
      const html = wrapper.html()
      for (const token of ['pythonImportPath', 'shellCommand', 'callable', 'sqlStatement']) {
        expect(html, `${token} leaked at filter ${cat}`).not.toContain(token)
      }
    }
  })
})
