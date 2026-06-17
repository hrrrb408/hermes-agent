/**
 * Phase 3B-Live-Enablement: KILL SWITCH rendering.
 *
 * Verifies the kill-switch-active state renders a blocked banner, keeps the
 * gate disabled, and never exposes a secret. Clearing the kill switch is not
 * itself an approval.
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

describe('Phase 3B-Live-Enablement kill switch', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedFetch.mockReset()
  })

  it('inactive by default — no kill banner', async () => {
    mockedFetch.mockResolvedValue(boundary({}))
    const store = useToolProviderStore()
    await store.loadBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    expect(store.liveStatus?.killSwitchActive).toBe(false)
    expect(wrapper.find('[data-testid="provider-live-kill-switch"]').exists()).toBe(false)
  })

  it('active state renders the kill banner with the trigger reason', async () => {
    mockedFetch.mockResolvedValue(
      boundary({ killSwitchActive: true, killSwitchTriggeredBy: 'secret_detected' }),
    )
    const store = useToolProviderStore()
    await store.loadBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const banner = wrapper.find('[data-testid="provider-live-kill-switch"]')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toContain('secret_detected')
    expect(wrapper.find('[data-testid="provider-live-label"]').text()).toContain('kill switch')
  })

  it('kill switch active keeps live disabled', async () => {
    mockedFetch.mockResolvedValue(
      boundary({ liveEnabled: true, killSwitchActive: true }),
    )
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveEnabled).toBe(false)
  })

  it('clearing the kill switch (inactive) does not grant live-enabled', async () => {
    // killSwitchActive false but liveEnabled still false → re-enable needs approval.
    mockedFetch.mockResolvedValue(boundary({ killSwitchActive: false, liveEnabled: false }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveStatus?.killSwitchActive).toBe(false)
    expect(store.liveEnabled).toBe(false)
  })
})
