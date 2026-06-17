/**
 * Phase 3B-Live-Enablement H1 — KILL SWITCH UI hardening (LIVE-KILL-3B-H1-001).
 *
 * Probes additional kill-switch rendering edge cases:
 *   - inactive by default → no kill banner
 *   - each of several trigger reasons renders in the banner
 *   - kill-active keeps live disabled even with the flag true
 *   - clearing (inactive) does NOT grant live-enabled (still needs approval)
 *   - the kill banner + triggered-by reason are value-free
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

const TRIGGERS = [
  'secret_detected',
  'budget_exceeded',
  'unexpected_provider_tool_call',
  'provider_write_autonomous_suggestion',
  'production_gateway_pid_drift',
]

describe('Phase 3B-Live-Enablement H1 kill switch UI hardening', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedFetch.mockReset()
  })

  it('inactive by default renders no kill banner', async () => {
    mockedFetch.mockResolvedValue(boundary({}))
    const store = useToolProviderStore()
    await store.loadBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    expect(store.liveStatus?.killSwitchActive).toBe(false)
    expect(wrapper.find('[data-testid="provider-live-kill-switch"]').exists()).toBe(false)
  })

  it.each(TRIGGERS)('renders the kill banner for trigger: %s', async (trigger) => {
    mockedFetch.mockResolvedValue(boundary({ killSwitchActive: true, killSwitchTriggeredBy: trigger }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const banner = wrapper.find('[data-testid="provider-live-kill-switch"]')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toContain(trigger)
  })

  it('kill-active keeps live disabled even with the flag true', async () => {
    mockedFetch.mockResolvedValue(boundary({ liveEnabled: true, killSwitchActive: true }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveEnabled).toBe(false)
  })

  it('clearing (inactive) does NOT grant live-enabled', async () => {
    mockedFetch.mockResolvedValue(boundary({ killSwitchActive: false, liveEnabled: false }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.liveStatus?.killSwitchActive).toBe(false)
    expect(store.liveEnabled).toBe(false)
  })

  it('kill banner payload is value-free', async () => {
    mockedFetch.mockResolvedValue(
      boundary({ killSwitchActive: true, killSwitchTriggeredBy: 'secret_detected' }),
    )
    const store = useToolProviderStore()
    await store.loadBoundary()
    const wrapper = mount(ProviderBoundaryStatusPanel)
    const html = wrapper.find('[data-testid="provider-live-kill-switch"]').html().toLowerCase()
    for (const needle of ['sk-', 'bearer', 'authorization', '/users/huangruibang/.hermes', 'state.db']) {
      expect(html).not.toContain(needle)
    }
  })
})
