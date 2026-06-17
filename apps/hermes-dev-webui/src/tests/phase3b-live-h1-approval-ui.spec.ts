/**
 * Phase 3B-Live-Enablement H1 — live APPROVAL UI hardening (LIVE-APPROVAL-3B-H1-001).
 *
 * Probes approval-state edge cases beyond the implementation tests:
 *   - default approval-required + absent + count 0
 *   - approval-present single-use state reflected in the store
 *   - approval-present-but-kill-active is NOT live-enabled
 *   - liveEnabled requires flag true AND kill switch inactive
 *   - the manualOneShot flag is false in every approval state (no implicit live)
 *   - the approval surface never exposes a forbidden secret needle
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

describe('Phase 3B-Live-Enablement H1 approval UI hardening', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedFetch.mockReset()
  })

  it('defaults to approval-required + absent + count 0', async () => {
    mockedFetch.mockResolvedValue(boundary({}))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveStatus?.approvalRequired).toBe(true)
    expect(store.liveStatus?.approvalPresent).toBe(false)
    expect(store.liveStatus?.approvalCount).toBe(0)
  })

  it('reflects a single-use approval-present state', async () => {
    mockedFetch.mockResolvedValue(boundary({ approvalPresent: true, approvalCount: 1 }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveStatus?.approvalPresent).toBe(true)
    expect(store.liveStatus?.approvalSingleUse).toBe(true)
    expect(store.liveStatus?.approvalCount).toBe(1)
  })

  it('approval-present but kill-active is NOT live-enabled', async () => {
    mockedFetch.mockResolvedValue(
      boundary({ approvalPresent: true, approvalCount: 1, killSwitchActive: true, liveEnabled: true }),
    )
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveStatus?.approvalPresent).toBe(true)
    expect(store.liveStatus?.killSwitchActive).toBe(true)
    expect(store.liveEnabled).toBe(false)
  })

  it('liveEnabled requires flag true AND kill switch inactive', async () => {
    mockedFetch.mockResolvedValue(boundary({ liveEnabled: true, killSwitchActive: false }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveEnabled).toBe(true)
  })

  it('manualOneShot stays false in every approval state', async () => {
    for (const live of [
      makeLive(),
      makeLive({ approvalPresent: true, approvalCount: 1 }),
      makeLive({ approvalPresent: true, killSwitchActive: true }),
    ]) {
      setActivePinia(createPinia())
      mockedFetch.mockResolvedValueOnce({ ...boundary({}), providerLive: live })
      const store = useToolProviderStore()
      await store.loadBoundary()
      expect(store.liveStatus?.manualOneShot).toBe(false)
    }
  })

  it('rendered approval surface carries no forbidden secret needle', async () => {
    mockedFetch.mockResolvedValue(boundary({ approvalPresent: true, approvalCount: 1 }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const html = wrapper.html().toLowerCase()
    for (const needle of FORBIDDEN_NEEDLES.map((n) => n.toLowerCase())) {
      expect(html).not.toContain(needle)
    }
    expect(wrapper.findAll('input[type="password"]').length).toBe(0)
  })
})
