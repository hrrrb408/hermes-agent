/**
 * Phase 3B: Real Provider disabled-state tests.
 *
 * Verifies the default boundary is disabled, real is not reachable by
 * default, and the UI surfaces the disabled label + the env_missing key
 * marker (never a key value).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import { fetchProviderBoundary } from '@/api/toolProvider'

vi.mock('@/api/toolProvider', () => ({
  fetchProviderBoundary: vi.fn(),
  runProviderRoundtrip: vi.fn(),
}))

const mockedFetch = vi.mocked(fetchProviderBoundary)

import { useToolProviderStore } from '@/stores/toolProvider'

describe('Phase 3B provider disabled state', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedFetch.mockReset()
  })

  it('defaults to disabled with no real reachability', async () => {
    mockedFetch.mockResolvedValue({
      providerMode: 'disabled',
      apiEnabled: false,
      providerName: 'openai_compatible',
      providerNameImplemented: true,
      baseUrlHost: '',
      baseUrlAllowed: false,
      model: '',
      modelAllowed: false,
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
    } as never)
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.boundaryLabel).toBe('disabled')
    expect(store.boundary?.realReachable).toBe(false)
    expect(store.boundary?.apiEnabled).toBe(false)
    expect(store.boundary?.apiKeySourceDetail).toBe('env_missing')
  })

  it('does not surface a key value when key is present', async () => {
    mockedFetch.mockResolvedValue({
      providerMode: 'disabled',
      apiEnabled: false,
      providerName: 'openai_compatible',
      providerNameImplemented: true,
      baseUrlHost: '',
      baseUrlAllowed: false,
      model: '',
      modelAllowed: false,
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
      gatingReason: 'blocked_provider_api_disabled',
      providerWriteBlocked: true,
      providerAutoWriteBlocked: true,
      autonomousWriteBlocked: true,
      productionRolloutBlocked: true,
      redactionApplied: true,
    } as never)
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.boundary?.apiKeySourceDetail).toBe('env_present')
    expect(store.boundary?.apiKeyPresent).toBe(true)
    // The boundary object must not contain a raw key value anywhere.
    const blob = JSON.stringify(store.boundary)
    for (const needle of ['sk-', 'Bearer ', 'Authorization', 'apiKeyValue']) {
      expect(blob).not.toContain(needle)
    }
  })
})
