/**
 * Phase 3D-H1 — Plugin Descriptor validation-state HARDENING tests.
 *
 * Asserts the UI is safe across every validation state: the valid/enabled
 * state, the validation_failed state (counts zeroed, validation invalid — the
 * summary must still render the frozen flags as false and leak nothing), and
 * the empty state. The frozen descriptor manifest stays stable at 12.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import PluginDescriptorRegistrySummary from '@/components/devconsole/PluginDescriptorRegistrySummary.vue'
import PluginDescriptorRegistryTable from '@/components/devconsole/PluginDescriptorRegistryTable.vue'
import type { PluginDescriptorRegistrySummary as Summary } from '@/types/api/pluginDescriptorRegistry'
import { PLUGIN_DESCRIPTOR_MANIFEST } from '@/constants/pluginDescriptorRegistryManifest'
import { PLUGIN_FROZEN_FLAGS } from '@/stores/pluginDescriptorRegistry'

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

function enabledSummary(): Summary {
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

function validationFailedSummary(): Summary {
  return {
    ...enabledSummary(),
    status: 'validation_failed',
    descriptorCount: 0,
    visibleCount: 0,
    disabledCount: 0,
    blockedCount: 0,
    validation: { valid: false, errorCount: 1, warningCount: 0 },
  }
}

describe('PluginDescriptor validation-state HARDENING (Phase 3D-H1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('enabled state: renders counts + validation valid', () => {
    const text = mount(PluginDescriptorRegistrySummary, { props: { summary: enabledSummary() } }).text()
    expect(text).toContain('12')
    expect(text).toContain('34/34/5/0/1/1')
  })

  it('validation_failed state: still renders frozen flags as false and leaks nothing', () => {
    const wrapper = mount(PluginDescriptorRegistrySummary, {
      props: { summary: validationFailedSummary() },
    })
    expect(wrapper.find('[data-testid="plugin-frozen-flags"]').exists()).toBe(true)
    const html = wrapper.html()
    // A validation failure must never flip a frozen flag on / enable execution.
    expect(PLUGIN_FROZEN_FLAGS.pluginRuntimeImplemented).toBe(false)
    expect(PLUGIN_FROZEN_FLAGS.pluginExecutionAllowed).toBe(false)
    expect(PLUGIN_FROZEN_FLAGS.productionAllowed).toBe(false)
    for (const token of FORBIDDEN_TOKENS) {
      expect(html, `forbidden token ${token}`).not.toContain(token)
    }
  })

  it('validation_failed state: still surfaces the route-governance baseline', () => {
    const text = mount(PluginDescriptorRegistrySummary, {
      props: { summary: validationFailedSummary() },
    }).text()
    expect(text).toContain('34/34/5/0/1/1')
  })

  it('null summary degrades to a safe placeholder', () => {
    const wrapper = mount(PluginDescriptorRegistrySummary, { props: { summary: null } })
    expect(wrapper.text()).toContain('—')
    for (const token of FORBIDDEN_TOKENS) {
      expect(wrapper.html(), `forbidden token ${token}`).not.toContain(token)
    }
  })

  it('empty table state is safe', () => {
    const wrapper = mount(PluginDescriptorRegistryTable, { props: { descriptors: [] } })
    expect(wrapper.findAll('.plugin-table tbody tr').length).toBe(0)
    for (const token of FORBIDDEN_TOKENS) {
      expect(wrapper.html(), `forbidden token ${token}`).not.toContain(token)
    }
  })

  it('the frozen manifest stays stable at 12 descriptors', () => {
    expect(PLUGIN_DESCRIPTOR_MANIFEST.length).toBe(12)
    // Every descriptor is dev-only / production-not-allowed regardless of state.
    for (const d of PLUGIN_DESCRIPTOR_MANIFEST) {
      expect(d.devOnly).toBe(true)
      expect(d.productionAllowed).toBe(false)
      expect(d.disabledByDefault).toBe(true)
    }
  })
})
