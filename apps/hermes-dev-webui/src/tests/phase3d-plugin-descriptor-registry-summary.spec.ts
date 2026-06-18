/**
 * Phase 3D — Plugin Descriptor Registry summary tests.
 *
 * Asserts the summary renders the frozen policy flags (all runtime flags =
 * false / disabled), the descriptor counts, and the route-governance baseline.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import PluginDescriptorRegistrySummary from '@/components/devconsole/PluginDescriptorRegistrySummary.vue'
import type { PluginDescriptorRegistrySummary as Summary } from '@/types/api/pluginDescriptorRegistry'

function sampleSummary(): Summary {
  return {
    status: 'enabled',
    registryVersion: 'phase3d-static-descriptor-v1',
    descriptorCount: 12,
    visibleCount: 3,
    disabledCount: 4,
    blockedCount: 5,
    devOnly: true,
    productionAllowed: false,
    pluginRuntimeImplemented: false,
    pluginLoaderImplemented: false,
    dynamicLoadingAllowed: false,
    localPluginDirectoryLoadingAllowed: false,
    remoteRegistryAllowed: false,
    marketplaceAllowed: false,
    externalPluginFetchAllowed: false,
    providerGeneratedPluginAllowed: false,
    llmGeneratedPluginInstallAllowed: false,
    pluginExecutionAllowed: false,
    newRouteIntroduced: false,
    routeGovernanceExpected: '34/34/5/0/1/1',
    validation: { valid: true, errorCount: 0, warningCount: 0 },
    redactionApplied: true,
  }
}

describe('PluginDescriptorRegistrySummary (Phase 3D)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the summary card', () => {
    const wrapper = mount(PluginDescriptorRegistrySummary, { props: { summary: sampleSummary() } })
    expect(wrapper.find('[data-testid="plugin-descriptor-registry-summary"]').exists()).toBe(true)
  })

  it('surfaces the live counts', () => {
    const wrapper = mount(PluginDescriptorRegistrySummary, { props: { summary: sampleSummary() } })
    const text = wrapper.text()
    expect(text).toContain('12')
    expect(text).toContain('34/34/5/0/1/1')
  })

  it('renders all frozen policy flags as disabled/false', () => {
    const wrapper = mount(PluginDescriptorRegistrySummary, { props: { summary: sampleSummary() } })
    const flags = wrapper.find('[data-testid="plugin-frozen-flags"]')
    expect(flags.exists()).toBe(true)
    const text = flags.text().toLowerCase()
    expect(text).toContain('plugin runtime implemented')
    expect(text).toContain('plugin loader implemented')
    expect(text).toContain('dynamic loading')
    expect(text).toContain('local plugin directory loading')
    expect(text).toContain('remote registry')
    expect(text).toContain('marketplace')
    expect(text).toContain('external plugin fetch')
    expect(text).toContain('provider-generated plugin')
    expect(text).toContain('llm-generated plugin install')
    expect(text).toContain('plugin execution')
    expect(text).toContain('new route introduced')
  })

  it('degrades gracefully when summary is null', () => {
    const wrapper = mount(PluginDescriptorRegistrySummary, { props: { summary: null } })
    expect(wrapper.text()).toContain('—')
  })
})
