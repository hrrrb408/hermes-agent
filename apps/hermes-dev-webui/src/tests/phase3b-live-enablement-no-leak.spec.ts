/**
 * Phase 3B-Live-Enablement: NO-LEAK hardening.
 *
 * Verifies the live-gate surface never renders an API-key input, an API-key
 * value, an Authorization / Bearer header, a raw token, a full tokenHash, a
 * raw prompt/response secret, a callable repr, or a production path — in any
 * rendered state.
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

const FORBIDDEN_NEEDLES = [
  'sk-', 'Bearer ', 'Authorization', 'apiKeyValue', 'accessToken',
  'refresh_token', 'client_secret', 'fullTokenHash', 'plainToken',
  '<function', '<bound method', '/Users/huangruibang/.hermes', 'state.db',
]

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

describe('Phase 3B-Live-Enablement no-leak', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedFetch.mockReset()
  })

  it('renders no API-key input in any live state', async () => {
    for (const live of [
      makeLive(),
      makeLive({ liveEnabled: true }),
      makeLive({ killSwitchActive: true, killSwitchTriggeredBy: 'budget_exceeded' }),
      makeLive({ approvalPresent: true, approvalCount: 1 }),
    ]) {
      setActivePinia(createPinia())
      mockedFetch.mockResolvedValue(boundary({}))
      const store = useToolProviderStore()
      // Inject the live payload directly via the mocked fetch variant.
      mockedFetch.mockResolvedValueOnce({ ...boundary({}), providerLive: live })
      await store.loadBoundary()
      const wrapper = mount(ProviderBoundaryStatusPanel)
      const html = wrapper.html()
      expect(html).not.toMatch(/api ?key/i)
      expect(wrapper.findAll('input[type="password"]').length).toBe(0)
    }
  })

  it('never carries a forbidden secret value in the live payload', async () => {
    mockedFetch.mockResolvedValue(boundary({ liveEnabled: true }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    const blob = JSON.stringify(store.liveStatus)
    for (const needle of FORBIDDEN_NEEDLES) {
      expect(blob).not.toContain(needle)
    }
  })

  it('the rendered live DOM never leaks a forbidden needle', async () => {
    mockedFetch.mockResolvedValue(boundary({ liveEnabled: true, approvalPresent: true }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const live = wrapper.find('[data-testid="provider-live-status"]')
    const html = live.html().toLowerCase()
    for (const needle of FORBIDDEN_NEEDLES.map((n) => n.toLowerCase())) {
      expect(html).not.toContain(needle)
    }
  })

  it('the manual one-shot flag is false by default (no real call)', async () => {
    mockedFetch.mockResolvedValue(boundary({}))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveStatus?.manualOneShot).toBe(false)
  })
})
