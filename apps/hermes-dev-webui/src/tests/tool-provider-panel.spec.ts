/**
 * Tests for the ProviderRoundtripPanel component (Phase 2B).
 *
 * Covers rendering of the mode selector, message input, allowed-tools
 * selector, schema/flags/results surfaces, the real-mode blocked message,
 * and the invariant that NO API key input element exists in the panel.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import ProviderRoundtripPanel from '@/components/workspace/ProviderRoundtripPanel.vue'
import { useToolProviderStore } from '@/stores/toolProvider'
import type { ProviderRoundtripResultData } from '@/types/api/toolProvider'

vi.mock('@/api/toolProvider', () => ({
  runProviderRoundtrip: vi.fn(),
  fetchProviderBoundary: vi.fn().mockResolvedValue(null),}))

function makeResult(overrides: Partial<ProviderRoundtripResultData> = {}): ProviderRoundtripResultData {
  return {
    status: 'completed',
    mode: 'provider_roundtrip',
    providerMode: 'fake',
    providerRequestId: 'prqs_test',
    providerResponseId: 'prsp_test',
    providerSchemaSent: true,
    providerApiCalled: true,
    externalNetworkCalled: false,
    readOnlyOnly: true,
    toolWriteDisabled: true,
    toolCalls: [
      { id: 'ptc_1', name: 'route_governance_read', arguments: { includeDetails: true }, status: 'valid', blockedReason: null },
    ],
    toolResults: [
      { toolCallId: 'ptc_1', toolId: 'route_governance_read', status: 'executed', executed: true, blockedReason: null },
    ],
    finalAnswer: 'Provider round-trip completed (fake provider).',
    providerAuditIds: ['prau_1', 'prau_2'],
    blockedReason: null,
    schemaSummary: {
      schemaVersion: 1, bundleVersion: 1, toolCount: 6,
      toolIds: ['clarify', 'tool_policy_read', 'route_governance_read'],
      readOnlyOnly: true, writeToolCount: 0, providerRecursiveToolCount: 0,
    },
    ...overrides,
  }
}

describe('ProviderRoundtripPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  function mountPanel() {
    return mount(ProviderRoundtripPanel, { attachTo: document.body })
  }

  it('renders the panel with mode selector and message input', () => {
    const wrapper = mountPanel()
    expect(wrapper.find('#provider-mode').exists()).toBe(true)
    expect(wrapper.find('#provider-message').exists()).toBe(true)
    expect(wrapper.text()).toContain('Provider Round-trip')
  })

  it('offers disabled / fake / real modes', () => {
    const wrapper = mountPanel()
    const options = wrapper.findAll('#provider-mode option')
    const values = options.map((o) => o.attributes('value'))
    expect(values).toEqual(['disabled', 'fake', 'real'])
  })

  it('renders the allowed-tools selector', () => {
    const wrapper = mountPanel()
    expect(wrapper.find('.provider-rt__tools').exists()).toBe(true)
    // read-only tools are listed
    expect(wrapper.text()).toContain('Route Governance')
  })

  it('shows the run button disabled when mode is not fake', () => {
    const wrapper = mountPanel()
    const btn = wrapper.find('button.provider-rt__btn--primary')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('displays the real-mode blocked message when real is selected', async () => {
    const wrapper = mountPanel()
    const store = useToolProviderStore()
    store.setProviderMode('real')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Real provider mode is blocked')
  })

  it('renders tool calls, results, and final answer after a completed run', async () => {
    const wrapper = mountPanel()
    const store = useToolProviderStore()
    store.setProviderMode('fake')
    store.result = makeResult()
    store.status = 'completed'
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('route_governance_read')
    expect(wrapper.text()).toContain('Provider round-trip completed')
    expect(wrapper.find('.provider-rt__audit').exists()).toBe(true)
  })

  it('shows the provider flags including externalNetworkCalled=false', async () => {
    const wrapper = mountPanel()
    const store = useToolProviderStore()
    store.result = makeResult()
    store.status = 'completed'
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('External network called')
    expect(wrapper.text()).toContain('false')
  })

  it('never renders an API key input', () => {
    const wrapper = mountPanel()
    const html = wrapper.html().toLowerCase()
    for (const forbidden of ['api key', 'apikey', 'api-key', 'authorization', 'bearer', 'secret']) {
      expect(html).not.toContain(forbidden)
    }
    // No input element whose id/name/placeholder references a key.
    const inputs = wrapper.findAll('input')
    for (const input of inputs) {
      const id = (input.attributes('id') || '').toLowerCase()
      const name = (input.attributes('name') || '').toLowerCase()
      const placeholder = (input.attributes('placeholder') || '').toLowerCase()
      expect(id + name + placeholder).not.toMatch(/key|token|secret|auth/)
    }
  })
})
