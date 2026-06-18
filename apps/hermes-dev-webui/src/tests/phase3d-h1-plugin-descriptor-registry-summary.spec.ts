/**
 * Phase 3D-H1 — Plugin Descriptor Registry summary HARDENING tests.
 *
 * Re-asserts the summary surfaces every frozen policy flag (all runtime flags =
 * false / disabled), the descriptor counts, the route-governance baseline, the
 * validation summary, and that the rendered summary leaks no forbidden token.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import PluginDescriptorRegistrySummary from '@/components/devconsole/PluginDescriptorRegistrySummary.vue'
import type { PluginDescriptorRegistrySummary as Summary } from '@/types/api/pluginDescriptorRegistry'

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

describe('PluginDescriptorRegistrySummary HARDENING (Phase 3D-H1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('renders the summary card + frozen-flags list', () => {
    const wrapper = mount(PluginDescriptorRegistrySummary, { props: { summary: sampleSummary() } })
    expect(wrapper.find('[data-testid="plugin-descriptor-registry-summary"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="plugin-frozen-flags"]').exists()).toBe(true)
  })

  it('surfaces the live counts and route governance baseline', () => {
    const text = mount(PluginDescriptorRegistrySummary, { props: { summary: sampleSummary() } }).text()
    expect(text).toContain('12')
    expect(text).toContain('34/34/5/0/1/1')
  })

  it('renders every frozen policy flag label (all disabled / false)', () => {
    const flags = mount(PluginDescriptorRegistrySummary, {
      props: { summary: sampleSummary() },
    }).find('[data-testid="plugin-frozen-flags"]')
    const text = flags.text().toLowerCase()
    for (const label of [
      'plugin runtime implemented',
      'plugin loader implemented',
      'dynamic loading',
      'local plugin directory loading',
      'remote registry',
      'marketplace',
      'external plugin fetch',
      'provider-generated plugin',
      'llm-generated plugin install',
      'plugin execution',
      'new route introduced',
      'production allowed',
    ]) {
      expect(text, `flag label ${label}`).toContain(label)
    }
  })

  it('surfaces the validation summary (valid / no errors)', () => {
    const text = mount(PluginDescriptorRegistrySummary, {
      props: { summary: sampleSummary() },
    }).text().toLowerCase()
    expect(text).toContain('validation')
  })

  it('degrades gracefully when summary is null', () => {
    const wrapper = mount(PluginDescriptorRegistrySummary, { props: { summary: null } })
    expect(wrapper.text()).toContain('—')
  })

  it('the rendered summary leaks no forbidden token', () => {
    const html = mount(PluginDescriptorRegistrySummary, {
      props: { summary: sampleSummary() },
    }).html()
    for (const token of FORBIDDEN_TOKENS) {
      expect(html, `forbidden token ${token}`).not.toContain(token)
    }
    expect(html).not.toContain('/Users/huangruibang/.hermes')
    expect(html).not.toContain('state.db')
  })
})
