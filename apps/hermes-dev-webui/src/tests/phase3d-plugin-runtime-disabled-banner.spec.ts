/**
 * Phase 3D — Plugin runtime disabled banner tests.
 *
 * Asserts the banner renders and surfaces every read-only disabled invariant
 * (runtime disabled, loader not implemented, dynamic loading disabled, local
 * plugin directory loading disabled, remote registry disabled, marketplace
 * disabled, external plugin fetch disabled, no provider-generated plugin, no
 * LLM-generated plugin install) as explicit text.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import PluginRuntimeDisabledBanner from '@/components/devconsole/PluginRuntimeDisabledBanner.vue'

describe('PluginRuntimeDisabledBanner (Phase 3D)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the banner', () => {
    const wrapper = mount(PluginRuntimeDisabledBanner)
    expect(wrapper.find('[data-testid="plugin-runtime-disabled-banner"]').exists()).toBe(true)
  })

  it('states plugin runtime disabled', () => {
    const text = mount(PluginRuntimeDisabledBanner).text().toLowerCase()
    expect(text).toContain('plugin runtime disabled')
  })

  it('states loader not implemented', () => {
    const text = mount(PluginRuntimeDisabledBanner).text().toLowerCase()
    expect(text).toContain('plugin loader not implemented')
  })

  it('states dynamic loading disabled', () => {
    const text = mount(PluginRuntimeDisabledBanner).text().toLowerCase()
    expect(text).toContain('dynamic loading disabled')
  })

  it('states local plugin directory loading disabled', () => {
    const text = mount(PluginRuntimeDisabledBanner).text().toLowerCase()
    expect(text).toContain('local plugin directory loading disabled')
  })

  it('states remote registry disabled', () => {
    const text = mount(PluginRuntimeDisabledBanner).text().toLowerCase()
    expect(text).toContain('remote registry disabled')
  })

  it('states marketplace disabled', () => {
    const text = mount(PluginRuntimeDisabledBanner).text().toLowerCase()
    expect(text).toContain('marketplace disabled')
  })

  it('states external plugin fetch disabled', () => {
    const text = mount(PluginRuntimeDisabledBanner).text().toLowerCase()
    expect(text).toContain('external plugin fetch disabled')
  })

  it('states no provider-generated / no LLM-generated plugin install', () => {
    const text = mount(PluginRuntimeDisabledBanner).text().toLowerCase()
    expect(text).toContain('no provider-generated plugin')
    expect(text).toContain('no llm-generated plugin install')
  })

  it('states does not execute a plugin / does not grant permission', () => {
    const text = mount(PluginRuntimeDisabledBanner).text().toLowerCase()
    expect(text).toContain('does not execute a plugin')
    expect(text).toContain('does not grant permission')
  })
})
