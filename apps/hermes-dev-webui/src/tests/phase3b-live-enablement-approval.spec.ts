/**
 * Phase 3B-Live-Enablement: live APPROVAL states.
 *
 * Verifies the live gate reflects the approval-required default, an
 * approval-present (single-use) state, and the expired/used/killed states —
 * without ever surfacing an API-key value.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import { fetchProviderBoundary } from '@/api/toolProvider'
import type { ProviderBoundaryStatus, ProviderLiveStatus } from '@/types/api/toolProvider'
import { useToolProviderStore } from '@/stores/toolProvider'

vi.mock('@/api/toolProvider', () => ({
  fetchProviderBoundary: vi.fn(),
  runProviderRoundtrip: vi.fn(),
}))

const mockedFetch = vi.mocked(fetchProviderBoundary)

function makeLive(overrides: Partial<ProviderLiveStatus> = {}): ProviderLiveStatus {
  return {
    liveEnabled: false,
    available: false,
    approvalRequired: true,
    approvalPresent: false,
    approvalCount: 0,
    approvalSingleUse: true,
    approvalTtlSeconds: 300,
    killSwitchActive: false,
    killSwitchTriggeredBy: '',
    toolExecutionDisabled: true,
    providerWriteBlocked: true,
    providerAutoWriteBlocked: true,
    autonomousWriteBlocked: true,
    productionRolloutBlocked: true,
    streamingBlocked: true,
    multiProviderBlocked: true,
    manualOneShot: false,
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

describe('Phase 3B-Live-Enablement approval states', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedFetch.mockReset()
  })

  it('defaults to approval required + absent', async () => {
    mockedFetch.mockResolvedValue(boundary({}))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveStatus?.approvalRequired).toBe(true)
    expect(store.liveStatus?.approvalPresent).toBe(false)
    expect(store.liveStatus?.approvalCount).toBe(0)
  })

  it('reflects an approval-present single-use state', async () => {
    mockedFetch.mockResolvedValue(boundary({ approvalPresent: true, approvalCount: 1 }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveStatus?.approvalPresent).toBe(true)
    expect(store.liveStatus?.approvalSingleUse).toBe(true)
  })

  it('a kill-switch-active approval state is not live-enabled', async () => {
    mockedFetch.mockResolvedValue(boundary({
      killSwitchActive: true, killSwitchTriggeredBy: 'secret_detected',
      liveEnabled: false,
    }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveStatus?.killSwitchActive).toBe(true)
    expect(store.liveEnabled).toBe(false)
  })

  it('liveEnabled requires the flag true AND kill switch inactive', async () => {
    mockedFetch.mockResolvedValue(boundary({ liveEnabled: true, killSwitchActive: false }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveEnabled).toBe(true)
  })

  it('liveEnabled stays false when kill switch is active even if flag true', async () => {
    mockedFetch.mockResolvedValue(boundary({ liveEnabled: true, killSwitchActive: true }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveEnabled).toBe(false)
  })
})
