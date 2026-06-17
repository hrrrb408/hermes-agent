/**
 * Phase 3B-Live-Enablement: BUDGET caps rendering.
 *
 * Verifies the frozen first-live caps (1 request, 1000 total, 200 output,
 * 5 cents, 0 retries, 60s) surface value-free under the live budget badge,
 * and that fail-closed-on-counter-error is asserted.
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

describe('Phase 3B-Live-Enablement budget caps', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedFetch.mockReset()
  })

  it('surfaces the frozen first-live caps', async () => {
    mockedFetch.mockResolvedValue(boundary({}))
    const store = useToolProviderStore()
    await store.loadBoundary()
    const b = store.liveStatus!.budget
    expect(b.maxRequests).toBe(1)
    expect(b.maxTotalTokens).toBe(1000)
    expect(b.maxInputTokens).toBe(800)
    expect(b.maxOutputTokens).toBe(200)
    expect(b.maxBudgetCents).toBe(5)
    expect(b.maxRuntimeSeconds).toBe(60)
    expect(b.maxRetries).toBe(0)
  })

  it('asserts fail-closed-on-counter-error', async () => {
    mockedFetch.mockResolvedValue(boundary({}))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveStatus!.budget.failClosedOnCounterError).toBe(true)
  })

  it('renders the caps block value-free', async () => {
    mockedFetch.mockResolvedValue(boundary({}))
    const store = useToolProviderStore()
    await store.loadBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const caps = wrapper.find('[data-testid="provider-live-caps"]').text()
    expect(caps).toContain('5c')
    expect(caps).not.toMatch(/sk-/i)
    expect(caps).not.toMatch(/bearer/i)
  })

  it('retry cap renders as 0 (no retry for the first live test)', async () => {
    mockedFetch.mockResolvedValue(boundary({}))
    const store = useToolProviderStore()
    await store.loadBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    expect(store.liveStatus!.budget.maxRetries).toBe(0)
    // The retry cap line shows 0.
    const capItems = wrapper.findAll('.provider-live__cap')
    const retryItem = capItems.find((n) => n.text().includes('Max retries'))
    expect(retryItem?.text()).toContain('0')
  })
})
