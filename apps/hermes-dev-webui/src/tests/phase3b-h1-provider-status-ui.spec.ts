/**
 * Phase 3B-H1: Provider status-UI HARDENING.
 *
 * Verifies the ProviderBoundaryStatus component renders the boundary metadata
 * across the disabled / fake / real-blocked / real-gated states, surfaces the
 * caps + model name + allowlisted host, and NEVER renders an API-key input, a
 * raw key, an Authorization/Bearer header, a full tokenHash, or a production path.
 *
 * Provider UI Security ID: PROVIDER-UI-3B-H1-001
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import ProviderBoundaryStatusPanel from '@/components/workspace/ProviderBoundaryStatus.vue'
import { useToolProviderStore } from '@/stores/toolProvider'
import type { ProviderBoundaryStatus } from '@/types/api/toolProvider'

vi.mock('@/api/toolProvider', () => ({
  fetchProviderBoundary: vi.fn().mockResolvedValue(null),
  runProviderRoundtrip: vi.fn(),
}))

function makeBoundary(overrides: Partial<ProviderBoundaryStatus> = {}): ProviderBoundaryStatus {
  return {
    providerMode: 'disabled',
    apiEnabled: false,
    providerName: 'openai_compatible',
    providerNameImplemented: true,
    baseUrlHost: '',
    baseUrlAllowed: false,
    model: '',
    modelAllowed: false,
    timeoutSeconds: 20,
    maxRetries: 2,
    dailyBudgetCents: 100,
    maxTokens: 1024,
    perMinuteRequestCap: 20,
    dailyRequestCap: 200,
    dailyTokenCap: 500000,
    apiKeySource: 'env',
    apiKeyPresent: false,
    apiKeySourceDetail: 'env_missing',
    isDevHome: true,
    realReachable: false,
    gatingReason: 'blocked_provider_real_not_enabled',
    providerWriteBlocked: true,
    providerAutoWriteBlocked: true,
    autonomousWriteBlocked: true,
    productionRolloutBlocked: true,
    redactionApplied: true,
    ...overrides,
  } as ProviderBoundaryStatus
}

const FORBIDDEN = [
  'sk-', 'Bearer ', 'Authorization', 'apiKeyValue', 'accessToken',
  'fullTokenHash', 'plainToken', '/Users/huangruibang/.hermes', 'state.db',
  '<function', '<bound method',
]

describe('Phase 3B-H1 provider status-UI hardening', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders the disabled state with the section present', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary({ providerMode: 'disabled' })
    const wrapper = mount(ProviderBoundaryStatusPanel)
    // The boundary section always renders (aria-label is stable across states).
    expect(wrapper.find('section[aria-label="Real provider boundary status"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="provider-boundary-label"]').text()).toContain('Disabled')
    const blob = wrapper.html()
    for (const needle of FORBIDDEN) {
      expect(blob).not.toContain(needle)
    }
  })

  it('renders the fake state and leaks nothing', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary({ providerMode: 'fake' })
    const wrapper = mount(ProviderBoundaryStatusPanel)
    expect(wrapper.find('section[aria-label="Real provider boundary status"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="provider-boundary-label"]').text()).toContain('Fake')
    const blob = wrapper.html()
    for (const needle of FORBIDDEN) {
      expect(blob).not.toContain(needle)
    }
  })

  it('renders the real-blocked state with the gating reason', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary({
      providerMode: 'real', apiEnabled: true, realReachable: false,
      gatingReason: 'blocked_provider_production_gate_drift',
      apiKeySourceDetail: 'env_present',
    })
    const wrapper = mount(ProviderBoundaryStatusPanel)
    expect(wrapper.get('[data-testid="provider-boundary-label"]').text()).toContain('Real — blocked')
    expect(wrapper.get('[data-testid="provider-boundary-reason"]').text()).toContain('production_gate_drift')
  })

  it('renders the real-gated state with the allowlisted host + model', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary({
      providerMode: 'real', apiEnabled: true, realReachable: true,
      baseUrlHost: 'api.openai.com', baseUrlAllowed: true,
      model: 'gpt-4o-mini', modelAllowed: true,
      apiKeySourceDetail: 'env_present', gatingReason: null,
    })
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const html = wrapper.html()
    expect(html).toContain('api.openai.com')
    expect(html).toContain('gpt-4o-mini')
    // Even gated, no secret may render.
    for (const needle of FORBIDDEN) {
      expect(html).not.toContain(needle)
    }
  })

  it('renders the permanently-blocked operations as blocked in every state', () => {
    for (const mode of ['disabled', 'fake', 'real'] as const) {
      setActivePinia(createPinia())
      const store = useToolProviderStore()
      store.boundary = makeBoundary({ providerMode: mode, realReachable: mode === 'real' })
      const wrapper = mount(ProviderBoundaryStatusPanel)
      const labels = wrapper.findAll('.provider-boundary__blocked-item').map((i) => i.text())
      expect(labels.some((t) => t.includes('Provider write'))).toBe(true)
      expect(labels.some((t) => t.includes('Autonomous write'))).toBe(true)
      expect(labels.some((t) => t.includes('Production rollout'))).toBe(true)
      for (const t of labels) expect(t).not.toContain('ALLOWED')
    }
  })

  it('renders no password / key input in any state', () => {
    for (const mode of ['disabled', 'fake', 'real'] as const) {
      setActivePinia(createPinia())
      const store = useToolProviderStore()
      store.boundary = makeBoundary({ providerMode: mode, realReachable: mode === 'real' })
      const wrapper = mount(ProviderBoundaryStatusPanel)
      expect(wrapper.findAll('input[type="password"]').length).toBe(0)
      expect(wrapper.html().toLowerCase()).not.toMatch(/api ?key|bearer|authorization/)
    }
  })
})
