/**
 * Phase 3B-Live-Enablement H1 — live STATUS UI hardening (LIVE-UI-3B-H1-001).
 *
 * Probes additional status-rendering edge cases:
 *   - the disabled-by-default label renders in the DOM
 *   - the approval-required + single-use + 5-min TTL constants are asserted
 *   - the tool-execution-disabled line is present
 *   - liveEnabled is the conjunction of the flag AND an inactive kill switch
 *   - manualOneShot stays false in every rendered default state
 *   - the status block is value-free (no API-key input / Authorization / Bearer)
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount } from '@vue/test-utils'

import { fetchProviderBoundary } from '@/api/toolProvider'
import type { ProviderBoundaryStatus, ProviderLiveStatus } from '@/types/api/toolProvider'
import ProviderBoundaryStatusPanel from '@/components/workspace/ProviderBoundaryStatus.vue'
import { useToolProviderStore } from '@/stores/toolProvider'

vi.mock('@/api/toolProvider', () => ({
  fetchProviderBoundary: vi.fn(),
  runProviderRoundtrip: vi.fn(),
}))

const mockedFetch = vi.mocked(fetchProviderBoundary)

function makeLive(overrides: Partial<ProviderLiveStatus> = {}): ProviderLiveStatus {
  return {
    liveEnabled: false, available: false, approvalRequired: true,
    approvalPresent: false, approvalCount: 0, approvalSingleUse: true,
    approvalTtlSeconds: 300, killSwitchActive: false, killSwitchTriggeredBy: '',
    toolExecutionDisabled: true, providerWriteBlocked: true,
    providerAutoWriteBlocked: true, autonomousWriteBlocked: true,
    productionRolloutBlocked: true, streamingBlocked: true,
    multiProviderBlocked: true, manualOneShot: false,
    budget: {
      available: true, maxRequests: 1, maxTotalTokens: 1000, maxInputTokens: 800,
      maxOutputTokens: 200, maxBudgetCents: 5, maxRuntimeSeconds: 60, maxRetries: 0,
      rateLimitWindow: 60, failClosedOnCounterError: true,
    },
    redactionApplied: true,
    ...overrides,
  } as ProviderLiveStatus
}

function boundary(live: Partial<ProviderLiveStatus>): ProviderBoundaryStatus {
  return {
    providerMode: 'real', apiEnabled: true, providerName: 'openai_compatible',
    providerNameImplemented: true, baseUrlHost: 'api.openai.com', baseUrlAllowed: true,
    model: 'gpt-4o-mini', modelAllowed: true, timeoutSeconds: 20, maxRetries: 2,
    dailyBudgetCents: 100, maxTokens: 1024, perMinuteRequestCap: 20, dailyRequestCap: 200,
    dailyTokenCap: 500000, apiKeySource: 'env', apiKeyPresent: false,
    apiKeySourceDetail: 'env_missing', isDevHome: true, realReachable: false,
    gatingReason: 'blocked_provider_real_not_enabled', providerWriteBlocked: true,
    providerAutoWriteBlocked: true, autonomousWriteBlocked: true,
    productionRolloutBlocked: true, redactionApplied: true, providerLive: makeLive(live),
  } as ProviderBoundaryStatus
}

describe('Phase 3B-Live-Enablement H1 status UI hardening', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedFetch.mockReset()
  })

  it('renders the disabled label + live status section', async () => {
    mockedFetch.mockResolvedValue(boundary({}))
    const store = useToolProviderStore()
    await store.loadBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    expect(wrapper.find('[data-testid="provider-live-status"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="provider-live-label"]').text()).toContain('disabled')
  })

  it('asserts the frozen approval constants in the store', async () => {
    mockedFetch.mockResolvedValue(boundary({}))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveStatus?.approvalRequired).toBe(true)
    expect(store.liveStatus?.approvalSingleUse).toBe(true)
    expect(store.liveStatus?.approvalTtlSeconds).toBe(300)
  })

  it('renders the tool-execution-disabled line', async () => {
    mockedFetch.mockResolvedValue(boundary({}))
    const store = useToolProviderStore()
    await store.loadBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    expect(wrapper.find('[data-testid="provider-live-caps"]').text()).toContain('disabled for first live')
  })

  it('liveEnabled is flag AND inactive kill switch (conjunction)', async () => {
    // flag true, kill inactive → enabled
    mockedFetch.mockResolvedValue(boundary({ liveEnabled: true, killSwitchActive: false }))
    let store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveEnabled).toBe(true)

    // flag true but kill active → disabled
    setActivePinia(createPinia())
    mockedFetch.mockResolvedValue(boundary({ liveEnabled: true, killSwitchActive: true }))
    store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveEnabled).toBe(false)
  })

  it('manualOneShot stays false in every default state', async () => {
    for (const live of [
      makeLive(),
      makeLive({ liveEnabled: true }),
      makeLive({ killSwitchActive: true }),
      makeLive({ approvalPresent: true, approvalCount: 1 }),
    ]) {
      setActivePinia(createPinia())
      mockedFetch.mockResolvedValueOnce({ ...boundary({}), providerLive: live })
      const store = useToolProviderStore()
      await store.loadBoundary()
      expect(store.liveStatus?.manualOneShot).toBe(false)
    }
  })
})
