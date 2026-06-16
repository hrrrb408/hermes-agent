/**
 * Phase 3B: Real Provider no-leak tests.
 *
 * Sweeps the provider surface (panel + boundary component) for every
 * forbidden value class: no API-key input control, no API-key value, no
 * Authorization / Bearer header, no raw token, no full tokenHash, no raw
 * arguments with a secret, no callable repr, no production path.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import ProviderRoundtripPanel from '@/components/workspace/ProviderRoundtripPanel.vue'
import ProviderBoundaryStatusPanel from '@/components/workspace/ProviderBoundaryStatus.vue'
import { useToolProviderStore } from '@/stores/toolProvider'
import type { ProviderBoundaryStatus } from '@/types/api/toolProvider'

vi.mock('@/api/toolProvider', () => ({
  fetchProviderBoundary: vi.fn().mockResolvedValue(null),
  runProviderRoundtrip: vi.fn(),
}))

function makeBoundary(): ProviderBoundaryStatus {
  return {
    providerMode: 'real', apiEnabled: true,
    providerName: 'openai_compatible', providerNameImplemented: true,
    baseUrlHost: 'api.openai.com', baseUrlAllowed: true,
    model: 'gpt-4o-mini', modelAllowed: true,
    timeoutSeconds: 20, maxRetries: 2, dailyBudgetCents: 100, maxTokens: 1024,
    perMinuteRequestCap: 20, dailyRequestCap: 200, dailyTokenCap: 500000,
    apiKeySource: 'env', apiKeyPresent: true, apiKeySourceDetail: 'env_present',
    isDevHome: true, realReachable: false,
    gatingReason: 'blocked_provider_api_key_missing',
    providerWriteBlocked: true, providerAutoWriteBlocked: true,
    autonomousWriteBlocked: true, productionRolloutBlocked: true,
    redactionApplied: true,
  } as ProviderBoundaryStatus
}

const FORBIDDEN = [
  'sk-', 'Bearer ', 'Authorization:', 'apiKeyValue', 'accessToken',
  'refresh_token', 'client_secret', '<function', '<bound method',
  '/Users/huangruibang/.hermes', 'state.db',
]

describe('Phase 3B provider no-leak', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders NO API-key input control in the round-trip panel', () => {
    const wrapper = mount(ProviderRoundtripPanel)
    // No password / key input, no key v-model binding, no paste target.
    const html = wrapper.html().toLowerCase()
    expect(html).not.toMatch(/api ?key|password|bearer|authorization/)
    expect(wrapper.findAll('input[type="password"]').length).toBe(0)
    expect(wrapper.find('[data-testid="provider-boundary-status"]').exists()).toBe(true)
  })

  it('renders no forbidden secret values in the boundary component', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const html = wrapper.html()
    for (const needle of FORBIDDEN) {
      expect(html).not.toContain(needle)
    }
  })

  it('never renders a raw key prefix or masked key', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const html = wrapper.html()
    // A partial / masked key is still a leak.
    expect(html).not.toMatch(/sk-\*+/i)
    expect(html).not.toMatch(/key:\s*sk-/i)
  })

  it('does not expose a full tokenHash field', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const html = wrapper.html().toLowerCase()
    expect(html).not.toContain('tokenhash')
  })
})
