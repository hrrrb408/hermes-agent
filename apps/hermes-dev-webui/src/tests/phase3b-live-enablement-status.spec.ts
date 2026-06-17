/**
 * Phase 3B-Live-Enablement: live enablement STATUS rendering.
 *
 * Verifies the strict manual one-shot live gate renders its disabled-by-default
 * state, the approval-required flag, the read-only caps, and the permanently
 * blocked flags — without an API-key input or any secret value.
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
      available: true,
      maxRequests: 1,
      maxTotalTokens: 1000,
      maxInputTokens: 800,
      maxOutputTokens: 200,
      maxBudgetCents: 5,
      maxRuntimeSeconds: 60,
      maxRetries: 0,
      rateLimitWindow: 60,
      failClosedOnCounterError: true,
    },
    redactionApplied: true,
    ...overrides,
  } as ProviderLiveStatus
}

function makeBoundary(liveOverrides: Partial<ProviderLiveStatus> = {}): ProviderBoundaryStatus {
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
    providerLive: makeLive(liveOverrides),
  } as ProviderBoundaryStatus
}

describe('Phase 3B-Live-Enablement status rendering', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedFetch.mockReset()
  })

  it('renders the live status section with disabled-by-default state', async () => {
    mockedFetch.mockResolvedValue(makeBoundary())
    const store = useToolProviderStore()
    await store.loadBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const live = wrapper.find('[data-testid="provider-live-status"]')
    expect(live.exists()).toBe(true)
    expect(wrapper.find('[data-testid="provider-live-label"]').text()).toContain('disabled')
  })

  it('exposes the approval-required + single-use + 5-min TTL state', async () => {
    mockedFetch.mockResolvedValue(makeBoundary())
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveStatus?.approvalRequired).toBe(true)
    expect(store.liveStatus?.approvalSingleUse).toBe(true)
    expect(store.liveStatus?.approvalTtlSeconds).toBe(300)
  })

  it('renders the frozen first-live caps', async () => {
    mockedFetch.mockResolvedValue(makeBoundary())
    const store = useToolProviderStore()
    await store.loadBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const caps = wrapper.find('[data-testid="provider-live-caps"]').text()
    expect(caps).toContain('1')          // max requests
    expect(caps).toContain('1000')       // max total tokens
    expect(caps).toContain('200')        // max output tokens
    expect(caps).toContain('5c')         // max budget
    expect(store.liveStatus?.budget.maxRetries).toBe(0)
  })

  it('renders tool execution as disabled for the first live request', async () => {
    mockedFetch.mockResolvedValue(makeBoundary())
    const store = useToolProviderStore()
    await store.loadBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const caps = wrapper.find('[data-testid="provider-live-caps"]').text()
    expect(caps).toContain('disabled for first live')
  })

  it('liveEnabled stays false when the live flag is false', async () => {
    mockedFetch.mockResolvedValue(makeBoundary())
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveEnabled).toBe(false)
  })
})
