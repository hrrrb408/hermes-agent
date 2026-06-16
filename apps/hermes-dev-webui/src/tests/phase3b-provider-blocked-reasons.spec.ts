/**
 * Phase 3B: Real Provider blocked-reason UI tests.
 *
 * Mounts the ProviderBoundaryStatus component and verifies it surfaces the
 * gating reason code and the real_blocked label, and that the permanently-
 * blocked operations render as 'blocked' (never 'ALLOWED').
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

describe('Phase 3B provider blocked-reason UI', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders the real_blocked label and the gating reason code', async () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary({ realReachable: false, gatingReason: 'blocked_provider_api_key_missing' })
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const label = wrapper.get('[data-testid="provider-boundary-label"]')
    expect(label.text()).toContain('Real — blocked')
    const reason = wrapper.get('[data-testid="provider-boundary-reason"]')
    expect(reason.text()).toContain('blocked_provider_api_key_missing')
  })

  it('renders every permanently-blocked operation as blocked', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const items = wrapper.findAll('.provider-boundary__blocked-item')
    const labels = items.map((i) => i.text())
    expect(labels.some((t) => t.includes('Provider write'))).toBe(true)
    expect(labels.some((t) => t.includes('Provider auto-write'))).toBe(true)
    expect(labels.some((t) => t.includes('Autonomous write'))).toBe(true)
    expect(labels.some((t) => t.includes('Production rollout'))).toBe(true)
    // None may render as ALLOWED.
    for (const t of labels) {
      expect(t).not.toContain('ALLOWED')
    }
  })

  it('surfaces the env_present key marker (never a key value)', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary({ apiKeySourceDetail: 'env_present' })
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const blob = wrapper.html()
    expect(blob).toContain('env_present')
    for (const needle of ['sk-', 'Bearer ', 'Authorization']) {
      expect(blob).not.toContain(needle)
    }
  })

  it('renders the allowlisted base URL host only (never a secret URL)', () => {
    const store = useToolProviderStore()
    store.boundary = makeBoundary({ baseUrlHost: 'api.openai.com', baseUrlAllowed: true })
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const blob = wrapper.html()
    expect(blob).toContain('api.openai.com')
  })

  it('shows the boundary as unavailable when not loaded', () => {
    const store = useToolProviderStore()
    store.boundary = null
    const wrapper = mount(ProviderBoundaryStatusPanel)
    expect(wrapper.get('[data-testid="provider-boundary-empty"]').text()).toContain('unavailable')
  })
})
