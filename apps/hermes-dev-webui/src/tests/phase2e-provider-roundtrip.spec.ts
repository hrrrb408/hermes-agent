/**
 * Phase 2E — Provider Round-trip section tests.
 *
 * The section reuses the existing ProviderRoundtripPanel and adds a unified
 * BlockedReasonPanel when the round-trip is blocked. Asserts the mode selector
 * renders, real mode is presented as blocked by design, no API-key input is
 * ever accepted, and the BlockedReasonPanel renders for a blocked result.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/toolProvider', () => ({ runProviderRoundtrip: vi.fn() }))

import { runProviderRoundtrip } from '@/api/toolProvider'
import ProviderSection from '@/components/devconsole/ProviderSection.vue'
import { useToolProviderStore } from '@/stores/toolProvider'
import type { ProviderRoundtripResultData } from '@/types/api/toolProvider'

describe('ProviderSection (Phase 2E)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(runProviderRoundtrip).mockReset()
    window.localStorage.clear()
  })

  it('renders the provider mode selector and real-blocked messaging', () => {
    const wrapper = mount(ProviderSection)
    expect(wrapper.find('#provider-mode').exists()).toBe(true)
    const text = wrapper.text()
    expect(text).toContain('Provider Round-trip')
    expect(text).toContain('Real provider mode is blocked by default')
  })

  it('never accepts an API key input', () => {
    const wrapper = mount(ProviderSection)
    expect(wrapper.findAll('input[type="password"]').length).toBe(0)
    // No input field is named/identified as an api-key field (prose mentioning
    // "no API key" is fine — that is the safety statement).
    const keyInputs = wrapper.findAll('input').filter((i) => {
      const id = (i.attributes('id') ?? '') + (i.attributes('name') ?? '') + (i.attributes('placeholder') ?? '')
      return /api[_-]?key/i.test(id)
    })
    expect(keyInputs.length).toBe(0)
  })

  it('renders the BlockedReasonPanel when a round-trip is blocked', async () => {
    const store = useToolProviderStore()
    const blocked: ProviderRoundtripResultData = {
      status: 'blocked', mode: 'provider_roundtrip', providerMode: 'real',
      providerRequestId: 'prq_1', providerResponseId: null,
      providerSchemaSent: false, providerApiCalled: false, externalNetworkCalled: false,
      readOnlyOnly: true, toolWriteDisabled: true, toolCalls: [], toolResults: [],
      finalAnswer: '', providerAuditIds: [],
      blockedReason: 'blocked_provider_real_mode_not_enabled',
      schemaSummary: { schemaVersion: 1, bundleVersion: 1, toolCount: 6, toolIds: [], readOnlyOnly: true, writeToolCount: 0, providerRecursiveToolCount: 0 },
    }
    store.result = blocked
    store.status = 'blocked'

    const wrapper = mount(ProviderSection)
    const panel = wrapper.find('[data-testid="dev-blocked-reason"]')
    expect(panel.exists()).toBe(true)
    expect(panel.text()).toContain('Real provider blocked')
    // Never suggests bypassing the boundary.
    expect(panel.text()).not.toMatch(/^\s*bypass/i)
  })
})
