/**
 * Phase 3B-H1: Provider blocked-reason HARDENING.
 *
 * Verifies the boundary component surfaces every gating reason code, every
 * permanently-blocked operation renders as 'blocked' (NEVER 'ALLOWED'), and
 * none of the reason surfaces leak a secret. Also verifies the unavailable
 * state and the allowlisted-host-only rendering.
 *
 * Provider Policy Hardening ID: PROVIDER-POLICY-3B-H1-001
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import ProviderBoundaryStatusPanel from '@/components/workspace/ProviderBoundaryStatus.vue'
import { useToolProviderStore } from '@/stores/toolProvider'
import type { ProviderBoundaryStatus } from '@/types/api/toolProvider'

function makeBoundary(overrides: Partial<ProviderBoundaryStatus> = {}): ProviderBoundaryStatus {
  return {
    providerMode: 'real',
    apiEnabled: true,
    providerName: 'openai_compatible',
    providerNameImplemented: true,
    baseUrlHost: 'api.openai.com',
    baseUrlAllowed: true,
    model: 'gpt-4o-mini',
    modelAllowed: true,
    timeoutSeconds: 20,
    maxRetries: 2,
    dailyBudgetCents: 100,
    maxTokens: 1024,
    perMinuteRequestCap: 20,
    dailyRequestCap: 200,
    dailyTokenCap: 500000,
    apiKeySource: 'env',
    apiKeyPresent: true,
    apiKeySourceDetail: 'env_present',
    isDevHome: true,
    realReachable: false,
    gatingReason: 'blocked_provider_production_gate_drift',
    providerWriteBlocked: true,
    providerAutoWriteBlocked: true,
    autonomousWriteBlocked: true,
    productionRolloutBlocked: true,
    redactionApplied: true,
    ...overrides,
  } as ProviderBoundaryStatus
}

const REASON_CODES = [
  'blocked_provider_real_not_enabled',
  'blocked_provider_api_disabled',
  'blocked_provider_name_not_supported',
  'blocked_provider_api_key_missing',
  'blocked_provider_not_dev_home',
  'blocked_provider_production_gate_drift',
  'blocked_provider_base_url_not_allowed',
  'blocked_provider_model_not_allowed',
  'blocked_provider_timeout_invalid',
]

describe('Phase 3B-H1 provider blocked-reason hardening', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders the real_blocked label for every gating reason code', () => {
    for (const reason of REASON_CODES) {
      setActivePinia(createPinia())
      const store = useToolProviderStore()
      store.boundary = makeBoundary({ realReachable: false, gatingReason: reason })
      const wrapper = mount(ProviderBoundaryStatusPanel)
      const label = wrapper.get('[data-testid="provider-boundary-label"]')
      expect(label.text()).toContain('Real — blocked')
      const reasonEl = wrapper.get('[data-testid="provider-boundary-reason"]')
      expect(reasonEl.text()).toContain(reason)
    }
  })

  it('renders all four permanently-blocked operations, none ALLOWED', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const labels = wrapper.findAll('.provider-boundary__blocked-item').map((i) => i.text())
    expect(labels.some((t) => t.includes('Provider write'))).toBe(true)
    expect(labels.some((t) => t.includes('Provider auto-write'))).toBe(true)
    expect(labels.some((t) => t.includes('Autonomous write'))).toBe(true)
    expect(labels.some((t) => t.includes('Production rollout'))).toBe(true)
    for (const t of labels) {
      expect(t).not.toContain('ALLOWED')
      expect(t.toLowerCase()).not.toContain('enabled')
    }
  })

  it('the env_present key marker is shown, never a value', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary({ apiKeySourceDetail: 'env_present' })
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const blob = wrapper.html()
    expect(blob).toContain('env_present')
    for (const needle of ['sk-', 'Bearer ', 'Authorization', 'apiKeyValue']) {
      expect(blob).not.toContain(needle)
    }
  })

  it('renders the allowlisted base URL HOST only (never a secret URL)', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary({ baseUrlHost: 'api.openai.com', baseUrlAllowed: true })
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const blob = wrapper.html()
    expect(blob).toContain('api.openai.com')
    // A secret-bearing query/path on the URL must never appear.
    expect(blob).not.toContain('token=')
    expect(blob).not.toContain('sk-')
  })

  it('shows unavailable when the boundary is not loaded', () => {
    const store = useToolProviderStore()
    store.boundary = null
    const wrapper = mount(ProviderBoundaryStatusPanel)
    expect(wrapper.get('[data-testid="provider-boundary-empty"]').text()).toContain('unavailable')
  })

  it('reason surface leaks no secret across every reason code', () => {
    for (const reason of REASON_CODES) {
      setActivePinia(createPinia())
      const store = useToolProviderStore()
      store.boundary = makeBoundary({ gatingReason: reason })
      const blob = mount(ProviderBoundaryStatusPanel).html()
      for (const needle of ['sk-', 'Bearer ', 'Authorization', '/Users/huangruibang/.hermes', 'state.db']) {
        expect(blob).not.toContain(needle)
      }
    }
  })
})
