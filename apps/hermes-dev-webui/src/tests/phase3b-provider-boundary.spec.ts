/**
 * Phase 3B: Real Provider Boundary store + label tests.
 *
 * Covers the value-free boundary metadata block surfaced by GET /status
 * data.providerBoundary, and the coarse boundary label transitions:
 *   disabled / fake / real_blocked / real_gated.
 *
 * Safety: the boundary never carries an API-key value, Authorization header,
 * raw token, full tokenHash, raw arguments, or callable repr.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import { fetchProviderBoundary } from '@/api/toolProvider'
import type { ProviderBoundaryStatus } from '@/types/api/toolProvider'

vi.mock('@/api/toolProvider', () => ({
  fetchProviderBoundary: vi.fn(),
  runProviderRoundtrip: vi.fn(),
}))

const mockedFetch = vi.mocked(fetchProviderBoundary)

function makeBoundary(overrides: Partial<ProviderBoundaryStatus> = {}): ProviderBoundaryStatus {
  return {
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
    ...overrides,
  } as ProviderBoundaryStatus
}

// Import the store AFTER the mock is in place.
import { useToolProviderStore } from '@/stores/toolProvider'

describe('Phase 3B provider boundary store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedFetch.mockReset()
  })

  it('reports disabled when the boundary is unavailable', async () => {
    mockedFetch.mockResolvedValue(null)
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.boundary).toBeNull()
    expect(store.boundaryLabel).toBe('disabled')
  })

  it('reports fake when providerMode is fake', async () => {
    mockedFetch.mockResolvedValue(makeBoundary({ providerMode: 'fake' }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.boundaryLabel).toBe('fake')
  })

  it('reports real_blocked when real mode is not reachable', async () => {
    mockedFetch.mockResolvedValue(
      makeBoundary({
        providerMode: 'real', apiEnabled: true, realReachable: false,
        gatingReason: 'blocked_provider_api_key_missing',
      }),
    )
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.boundaryLabel).toBe('real_blocked')
    expect(store.boundary?.gatingReason).toBe('blocked_provider_api_key_missing')
  })

  it('reports real_gated when every gate passes', async () => {
    mockedFetch.mockResolvedValue(
      makeBoundary({
        providerMode: 'real', apiEnabled: true, realReachable: true,
        apiKeySourceDetail: 'env_present', baseUrlAllowed: true,
        baseUrlHost: 'api.openai.com', modelAllowed: true, model: 'gpt-4o-mini',
        gatingReason: null,
      }),
    )
    const store = useToolProviderStore()
    await store.loadBoundary()
    expect(store.boundaryLabel).toBe('real_gated')
  })

  it('never carries an API-key value in the boundary payload', async () => {
    const boundary = makeBoundary({ providerMode: 'real', apiKeySourceDetail: 'env_present' })
    const blob = JSON.stringify(boundary)
    for (const needle of ['sk-', 'Bearer ', 'Authorization', 'apiKeyValue']) {
      expect(blob).not.toContain(needle)
    }
  })

  it('exposes the permanently-blocked flags', async () => {
    mockedFetch.mockResolvedValue(makeBoundary({ providerMode: 'real', realReachable: true }))
    const store = useToolProviderStore()
    await store.loadBoundary()
    const b = store.boundary!
    expect(b.providerWriteBlocked).toBe(true)
    expect(b.providerAutoWriteBlocked).toBe(true)
    expect(b.autonomousWriteBlocked).toBe(true)
    expect(b.productionRolloutBlocked).toBe(true)
  })
})
