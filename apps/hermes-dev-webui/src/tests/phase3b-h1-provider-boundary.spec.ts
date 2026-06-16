/**
 * Phase 3B-H1: Provider Boundary store + label HARDENING.
 *
 * Adversarial verification of the coarse boundary label state machine and the
 * value-free invariant of the boundary payload. Real provider may never become
 * 'real_gated' without every gate passing; the boundary never carries an
 * API-key value, Authorization header, raw token, full tokenHash, or callable repr.
 *
 * Hardening ID: HARDENING-3B-H1-001
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

const FORBIDDEN_VALUE_NEEDLES = [
  'sk-', 'Bearer ', 'Authorization', 'apiKeyValue', 'accessToken',
  'refresh_token', 'client_secret', 'fullTokenHash', 'plainToken',
  '<function', '<bound method', '/Users/huangruibang/.hermes', 'state.db',
]

import { useToolProviderStore } from '@/stores/toolProvider'

describe('Phase 3B-H1 provider boundary label hardening', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedFetch.mockReset()
  })

  it('defaults to disabled when the boundary is null', async () => {
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

  it('reports real_blocked when real is selected but not reachable (every block reason)', async () => {
    const reasons = [
      'blocked_provider_real_not_enabled',
      'blocked_provider_api_disabled',
      'blocked_provider_api_key_missing',
      'blocked_provider_not_dev_home',
      'blocked_provider_production_gate_drift',
      'blocked_provider_base_url_not_allowed',
      'blocked_provider_model_not_allowed',
    ]
    for (const reason of reasons) {
      setActivePinia(createPinia())
      mockedFetch.mockResolvedValue(
        makeBoundary({ providerMode: 'real', apiEnabled: true, realReachable: false, gatingReason: reason }),
      )
      const store = useToolProviderStore()
      await store.loadBoundary()
      expect(store.boundaryLabel).toBe('real_blocked')
      expect(store.boundary?.realReachable).toBe(false)
    }
  })

  it('reports real_gated ONLY when realReachable is true', async () => {
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

  it('exposes the four permanently-blocked flags as true in every state', async () => {
    for (const mode of ['disabled', 'fake', 'real'] as const) {
      setActivePinia(createPinia())
      mockedFetch.mockResolvedValue(makeBoundary({ providerMode: mode, realReachable: mode === 'real' }))
      const store = useToolProviderStore()
      await store.loadBoundary()
      const b = store.boundary!
      expect(b.providerWriteBlocked).toBe(true)
      expect(b.providerAutoWriteBlocked).toBe(true)
      expect(b.autonomousWriteBlocked).toBe(true)
      expect(b.productionRolloutBlocked).toBe(true)
    }
  })

  it('never carries a forbidden secret value in ANY boundary payload', async () => {
    mockedFetch.mockResolvedValue(
      makeBoundary({ providerMode: 'real', apiEnabled: true, apiKeySourceDetail: 'env_present' }),
    )
    const store = useToolProviderStore()
    await store.loadBoundary()
    const blob = JSON.stringify(store.boundary)
    for (const needle of FORBIDDEN_VALUE_NEEDLES) {
      expect(blob).not.toContain(needle)
    }
  })

  it('the key marker is value-free (env_present / env_missing only)', async () => {
    for (const detail of ['env_present', 'env_missing'] as const) {
      setActivePinia(createPinia())
      mockedFetch.mockResolvedValue(makeBoundary({ apiKeySourceDetail: detail }))
      const store = useToolProviderStore()
      await store.loadBoundary()
      expect(store.boundary?.apiKeySource).toBe('env')
      expect(['env_present', 'env_missing']).toContain(store.boundary?.apiKeySourceDetail)
    }
  })
})
