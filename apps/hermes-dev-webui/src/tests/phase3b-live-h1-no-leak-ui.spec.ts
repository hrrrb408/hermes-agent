/**
 * Phase 3B-Live-Enablement H1 — NO-LEAK UI hardening (LIVE-UI-3B-H1-001).
 *
 * An exhaustive no-leak sweep across MANY live states: the live-gate surface
 * never renders an API-key input, an API-key value, an Authorization / Bearer
 * header, a raw token, a full tokenHash, a raw prompt/response secret, a
 * callable repr, or a production path — in any rendered state.
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
  'rawPrompt', 'rawResponse', '<function', '<bound method',
  '/Users/huangruibang/.hermes', 'state.db',
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

const STATES: Array<Partial<ProviderLiveStatus>> = [
  {},
  { liveEnabled: true },
  { approvalPresent: true, approvalCount: 1 },
  { killSwitchActive: true, killSwitchTriggeredBy: 'secret_detected' },
  { killSwitchActive: true, killSwitchTriggeredBy: 'budget_exceeded' },
  { liveEnabled: true, killSwitchActive: true },
  { approvalPresent: true, killSwitchActive: true },
]

describe('Phase 3B-Live-Enablement H1 no-leak UI hardening', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedFetch.mockReset()
  })

  it('renders no API-key input in every live state', async () => {
    for (const live of STATES) {
      setActivePinia(createPinia())
      mockedFetch.mockResolvedValueOnce({ ...boundary({}), providerLive: makeLive(live) })
      const store = useToolProviderStore()
      await store.loadBoundary()
      const wrapper = mount(ProviderBoundaryStatusPanel)
      expect(wrapper.findAll('input[type="password"]').length).toBe(0)
      expect(wrapper.html()).not.toMatch(/api ?key/i)
    }
  })

  it('the live payload never carries a forbidden secret in any state', async () => {
    for (const live of STATES) {
      setActivePinia(createPinia())
      mockedFetch.mockResolvedValueOnce({ ...boundary({}), providerLive: makeLive(live) })
      const store = useToolProviderStore()
      await store.loadBoundary()
      const blob = JSON.stringify(store.liveStatus)
      for (const needle of FORBIDDEN_NEEDLES) {
        expect(blob).not.toContain(needle)
      }
    }
  })

  it('the rendered live DOM never leaks a forbidden needle in any state', async () => {
    for (const live of STATES) {
      setActivePinia(createPinia())
      mockedFetch.mockResolvedValueOnce({ ...boundary({}), providerLive: makeLive(live) })
      const store = useToolProviderStore()
      await store.loadBoundary()
      const wrapper = mount(ProviderBoundaryStatusPanel)
      const liveSection = wrapper.find('[data-testid="provider-live-status"]')
      const html = (liveSection.exists() ? liveSection.html() : wrapper.html()).toLowerCase()
      for (const needle of FORBIDDEN_NEEDLES.map((n) => n.toLowerCase())) {
        expect(html).not.toContain(needle)
      }
    }
  })
})
