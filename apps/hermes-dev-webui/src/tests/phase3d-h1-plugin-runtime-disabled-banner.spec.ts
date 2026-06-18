/**
 * Phase 3D-H1 — Plugin runtime disabled banner HARDENING tests.
 *
 * Re-asserts the banner renders every read-only disabled invariant as explicit
 * text, carries an accessible role (status / polite live region), and leaks no
 * forbidden token. The banner is the canonical "no plugin runtime / no loader /
 * no dynamic loading / no local dir / no remote / no marketplace / no external
 * fetch / no provider-generated / no LLM-generated install" surface.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import PluginRuntimeDisabledBanner from '@/components/devconsole/PluginRuntimeDisabledBanner.vue'

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

describe('PluginRuntimeDisabledBanner HARDENING (Phase 3D-H1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the banner with the descriptor-only header', () => {
    const wrapper = mount(PluginRuntimeDisabledBanner)
    expect(wrapper.find('[data-testid="plugin-runtime-disabled-banner"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('descriptor-only registry')
  })

  it('carries an accessible status role + polite live region', () => {
    const wrapper = mount(PluginRuntimeDisabledBanner)
    const banner = wrapper.find('[data-testid="plugin-runtime-disabled-banner"]')
    expect(banner.attributes('role')).toBe('status')
    expect(banner.attributes('aria-live')).toBe('polite')
  })

  it('states every frozen disabled invariant as text', () => {
    const text = mount(PluginRuntimeDisabledBanner).text().toLowerCase()
    expect(text).toContain('plugin runtime disabled')
    expect(text).toContain('plugin loader not implemented')
    expect(text).toContain('dynamic loading disabled')
    expect(text).toContain('local plugin directory loading disabled')
    expect(text).toContain('remote registry disabled')
    expect(text).toContain('marketplace disabled')
    expect(text).toContain('external plugin fetch disabled')
    expect(text).toContain('no provider-generated plugin')
    expect(text).toContain('no llm-generated plugin install')
  })

  it('states does not execute a plugin / does not grant permission', () => {
    const text = mount(PluginRuntimeDisabledBanner).text().toLowerCase()
    expect(text).toContain('does not execute a plugin')
    expect(text).toContain('does not grant permission')
  })

  it('the banner leaks no forbidden token', () => {
    const html = mount(PluginRuntimeDisabledBanner).html()
    for (const token of FORBIDDEN_TOKENS) {
      expect(html, `forbidden token ${token}`).not.toContain(token)
    }
    expect(html).not.toContain('/Users/huangruibang/.hermes')
    expect(html).not.toContain('state.db')
  })

  it('renders exactly one list row per disabled invariant', () => {
    const wrapper = mount(PluginRuntimeDisabledBanner)
    const rows = wrapper.findAll('.plugin-runtime-disabled-banner__list li')
    // runtime / loader / dynamic / local dir / remote / marketplace / external fetch / no-provider-llm
    expect(rows.length).toBeGreaterThanOrEqual(8)
  })
})
