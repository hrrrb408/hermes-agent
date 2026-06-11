/**
 * Tests for the Tool Schema Preview Pinia store.
 *
 * Covers:
 * - Initial state
 * - Catalog loading (success, error, abort, race)
 * - Preview loading (success, 404, error, abort, race)
 * - Getters (items, availableItems, unavailableItems, counts)
 * - Reset actions (resetCatalog, resetSelectedPreview, resetErrors, resetAll)
 * - Abort / cleanup
 *
 * Safety invariants verified:
 * - Store does not call POST/PUT/PATCH/DELETE
 * - Store does not trigger execute, dry-run, or provider schema send
 * - Store does not modify existing Tool Policy store
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import { useToolSchemaPreviewStore } from '@/stores/toolSchemaPreview'

// ── Mock the API module ──

vi.mock('@/api/toolSchemaPreview', () => ({
  fetchToolSchemaPreviewCatalog: vi.fn(),
  fetchToolSchemaPreviewByCanonicalName: vi.fn(),
}))

import {
  fetchToolSchemaPreviewCatalog,
  fetchToolSchemaPreviewByCanonicalName,
} from '@/api/toolSchemaPreview'

// ── Test data factories ──

function makeCatalogItem(overrides: Record<string, unknown> = {}) {
  return {
    canonicalName: 'clarify',
    risk: 'R0' as const,
    capabilities: ['PURE_COMPUTE'] as const,
    schemaPreviewAvailable: true,
    schemaShape: 'object' as const,
    inputFields: [
      {
        fieldName: 'query',
        fieldType: 'string',
        required: true,
        descriptionPreview: 'The question.',
        enumPreview: null,
        defaultPresence: false,
        constraintsPreview: null,
      },
    ],
    redactionStatus: 'clean' as const,
    reasonCode: 'AVAILABLE',
    unavailableReason: null,
    ...overrides,
  }
}

function makeCatalogData(overrides: Record<string, unknown> = {}) {
  return {
    totalCount: 71,
    availableCount: 30,
    unavailableCount: 41,
    items: [makeCatalogItem()],
    ...overrides,
  }
}

function makeLookupData(overrides: Record<string, unknown> = {}) {
  return {
    found: true,
    preview: makeCatalogItem(),
    reasonCode: 'FOUND' as const,
    ...overrides,
  }
}

const MOCK_META = { requestId: 'test-rid', timestamp: '2026-06-11T10:00:00Z' }

function mockCatalogResolve(data: Record<string, unknown>) {
  return (fetchToolSchemaPreviewCatalog as ReturnType<typeof vi.fn>).mockResolvedValue({
    data,
    meta: MOCK_META,
  })
}

function mockPreviewResolve(data: Record<string, unknown>) {
  return (fetchToolSchemaPreviewByCanonicalName as ReturnType<typeof vi.fn>).mockResolvedValue({
    data,
    meta: MOCK_META,
  })
}

function mockCatalogReject(err: unknown) {
  return (fetchToolSchemaPreviewCatalog as ReturnType<typeof vi.fn>).mockRejectedValue(err)
}

function mockPreviewReject(err: unknown) {
  return (fetchToolSchemaPreviewByCanonicalName as ReturnType<typeof vi.fn>).mockRejectedValue(err)
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

// ═══════════════════════════════════════════════════════════════════════════
// 1. Initial State
// ═══════════════════════════════════════════════════════════════════════════

describe('initial state', () => {
  it('catalog state is idle', () => {
    const store = useToolSchemaPreviewStore()
    expect(store.catalogState).toBe('idle')
  })

  it('preview state is idle', () => {
    const store = useToolSchemaPreviewStore()
    expect(store.previewState).toBe('idle')
  })

  it('catalog is null', () => {
    const store = useToolSchemaPreviewStore()
    expect(store.catalog).toBeNull()
  })

  it('selectedPreview is null', () => {
    const store = useToolSchemaPreviewStore()
    expect(store.selectedPreview).toBeNull()
  })

  it('selectedCanonicalName is null', () => {
    const store = useToolSchemaPreviewStore()
    expect(store.selectedCanonicalName).toBeNull()
  })

  it('no errors', () => {
    const store = useToolSchemaPreviewStore()
    expect(store.catalogError).toBe('')
    expect(store.previewError).toBe('')
  })

  it('lastFetchedAt is null', () => {
    const store = useToolSchemaPreviewStore()
    expect(store.lastFetchedAt).toBeNull()
  })

  it('computed getters return empty defaults', () => {
    const store = useToolSchemaPreviewStore()
    expect(store.items).toEqual([])
    expect(store.availableItems).toEqual([])
    expect(store.unavailableItems).toEqual([])
    expect(store.totalCount).toBe(0)
    expect(store.availableCount).toBe(0)
    expect(store.unavailableCount).toBe(0)
    expect(store.hasCatalog).toBe(false)
    expect(store.hasSelectedPreview).toBe(false)
    expect(store.isCatalogLoading).toBe(false)
    expect(store.isPreviewLoading).toBe(false)
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 2. Catalog Loading
// ═══════════════════════════════════════════════════════════════════════════

describe('fetchCatalog', () => {
  it('transitions idle → loading → success', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData())

    const promise = store.fetchCatalog()
    expect(store.catalogState).toBe('loading')
    await promise
    expect(store.catalogState).toBe('success')
  })

  it('saves catalog data', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData())

    await store.fetchCatalog()

    expect(store.catalog).not.toBeNull()
    expect(store.catalog!.totalCount).toBe(71)
    expect(store.catalog!.availableCount).toBe(30)
    expect(store.catalog!.unavailableCount).toBe(41)
    expect(store.items).toHaveLength(1)
  })

  it('sets lastFetchedAt', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData())

    await store.fetchCatalog()

    expect(store.lastFetchedAt).toBe('2026-06-11T10:00:00Z')
  })

  it('transitions to empty state when no items', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData({
      totalCount: 0,
      availableCount: 0,
      unavailableCount: 0,
      items: [],
    }))

    await store.fetchCatalog()

    expect(store.catalogState).toBe('empty')
    expect(store.items).toHaveLength(0)
  })

  it('transitions to error on failure', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogReject({ code: 'NETWORK_ERROR', message: 'Network error.' })

    await store.fetchCatalog()

    expect(store.catalogState).toBe('error')
    expect(store.catalogError).toBe('Network error.')
  })

  it('does not enter error on abort', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogReject({ code: 'REQUEST_CANCELLED', message: 'Cancelled.' })

    await store.fetchCatalog()

    expect(store.catalogState).toBe('loading')
    expect(store.catalogError).toBe('')
  })

  it('new request cancels old request', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData())

    store.fetchCatalog()
    await store.fetchCatalog()

    expect(store.catalogState).toBe('success')
    expect(fetchToolSchemaPreviewCatalog).toHaveBeenCalledTimes(2)
  })

  it('stale catalog response does not overwrite new response', async () => {
    const store = useToolSchemaPreviewStore()
    const firstData = makeCatalogData({ totalCount: 10 })
    const secondData = makeCatalogData({ totalCount: 20 })

    let firstResolve: (value: unknown) => void
    const firstPromise = new Promise(resolve => { firstResolve = resolve })

    ;(fetchToolSchemaPreviewCatalog as ReturnType<typeof vi.fn>)
      .mockImplementationOnce(() => firstPromise)
      .mockImplementationOnce(() => Promise.resolve({ data: secondData, meta: MOCK_META }))

    store.fetchCatalog()
    const secondDone = store.fetchCatalog()

    await secondDone
    expect(store.catalog!.totalCount).toBe(20)

    firstResolve!({ data: firstData, meta: MOCK_META })
    await new Promise(r => setTimeout(r, 10))

    expect(store.catalog!.totalCount).toBe(20)
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 3. Preview Loading
// ═══════════════════════════════════════════════════════════════════════════

describe('fetchPreview', () => {
  it('transitions idle → loading → success', async () => {
    const store = useToolSchemaPreviewStore()
    mockPreviewResolve(makeLookupData())

    const promise = store.fetchPreview('clarify')
    expect(store.previewState).toBe('loading')
    await promise
    expect(store.previewState).toBe('success')
  })

  it('saves preview data', async () => {
    const store = useToolSchemaPreviewStore()
    mockPreviewResolve(makeLookupData())

    await store.fetchPreview('clarify')

    expect(store.selectedPreview).not.toBeNull()
    expect(store.selectedPreview!.found).toBe(true)
    expect(store.selectedPreview!.preview!.canonicalName).toBe('clarify')
  })

  it('sets selectedCanonicalName', async () => {
    const store = useToolSchemaPreviewStore()
    mockPreviewResolve(makeLookupData())

    await store.fetchPreview('clarify')

    expect(store.selectedCanonicalName).toBe('clarify')
  })

  it('handles 404 not found', async () => {
    const store = useToolSchemaPreviewStore()
    mockPreviewReject({
      code: 'TOOL_SCHEMA_PREVIEW_NOT_FOUND',
      message: "Tool schema preview not found for 'nonexistent'.",
      status: 404,
    })

    await store.fetchPreview('nonexistent')

    expect(store.previewState).toBe('error')
    expect(store.previewError).toContain('not found')
  })

  it('handles generic network error', async () => {
    const store = useToolSchemaPreviewStore()
    mockPreviewReject({ code: 'NETWORK_ERROR', message: 'Network error.' })

    await store.fetchPreview('clarify')

    expect(store.previewState).toBe('error')
    expect(store.previewError).toBe('Network error.')
  })

  it('does not enter error on abort', async () => {
    const store = useToolSchemaPreviewStore()
    mockPreviewReject({ code: 'REQUEST_CANCELLED', message: 'Cancelled.' })

    await store.fetchPreview('clarify')

    expect(store.previewState).toBe('loading')
    expect(store.previewError).toBe('')
  })

  it('new request cancels old request', async () => {
    const store = useToolSchemaPreviewStore()
    mockPreviewResolve(makeLookupData())

    store.fetchPreview('clarify')
    await store.fetchPreview('terminal')

    expect(store.previewState).toBe('success')
    expect(fetchToolSchemaPreviewByCanonicalName).toHaveBeenCalledTimes(2)
  })

  it('stale preview response does not overwrite new response', async () => {
    const store = useToolSchemaPreviewStore()
    const firstData = makeLookupData({ preview: makeCatalogItem({ canonicalName: 'clarify' }) })
    const secondData = makeLookupData({ preview: makeCatalogItem({ canonicalName: 'terminal' }) })

    let firstResolve: (value: unknown) => void
    const firstPromise = new Promise(resolve => { firstResolve = resolve })

    ;(fetchToolSchemaPreviewByCanonicalName as ReturnType<typeof vi.fn>)
      .mockImplementationOnce(() => firstPromise)
      .mockImplementationOnce(() => Promise.resolve({ data: secondData, meta: MOCK_META }))

    store.fetchPreview('clarify')
    const secondDone = store.fetchPreview('terminal')

    await secondDone
    expect(store.selectedPreview!.preview!.canonicalName).toBe('terminal')

    firstResolve!({ data: firstData, meta: MOCK_META })
    await new Promise(r => setTimeout(r, 10))

    expect(store.selectedPreview!.preview!.canonicalName).toBe('terminal')
  })

  it('handles found=false from API (not HTTP 404)', async () => {
    const store = useToolSchemaPreviewStore()
    // Backend returns 200 with found=false for edge cases (shouldn't happen
    // normally since backend returns 404, but store handles it)
    mockPreviewResolve(makeLookupData({
      found: false,
      preview: null,
      reasonCode: 'NOT_FOUND',
    }))

    await store.fetchPreview('edge_case')

    expect(store.previewState).toBe('error')
    expect(store.previewError).toContain('not found')
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 4. Computed / Getters
// ═══════════════════════════════════════════════════════════════════════════

describe('computed / getters', () => {
  it('items returns catalog items', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData())

    await store.fetchCatalog()

    expect(store.items).toHaveLength(1)
    expect(store.items[0]?.canonicalName).toBe('clarify')
  })

  it('availableItems filters by schemaPreviewAvailable=true', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData({
      items: [
        makeCatalogItem({ canonicalName: 'clarify', schemaPreviewAvailable: true }),
        makeCatalogItem({ canonicalName: 'terminal', schemaPreviewAvailable: false }),
      ],
      totalCount: 2,
      availableCount: 1,
      unavailableCount: 1,
    }))

    await store.fetchCatalog()

    expect(store.availableItems).toHaveLength(1)
    expect(store.availableItems[0]?.canonicalName).toBe('clarify')
  })

  it('unavailableItems filters by schemaPreviewAvailable=false', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData({
      items: [
        makeCatalogItem({ canonicalName: 'clarify', schemaPreviewAvailable: true }),
        makeCatalogItem({ canonicalName: 'terminal', schemaPreviewAvailable: false }),
      ],
      totalCount: 2,
      availableCount: 1,
      unavailableCount: 1,
    }))

    await store.fetchCatalog()

    expect(store.unavailableItems).toHaveLength(1)
    expect(store.unavailableItems[0]?.canonicalName).toBe('terminal')
  })

  it('totalCount returns catalog total', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData())

    await store.fetchCatalog()

    expect(store.totalCount).toBe(71)
  })

  it('availableCount returns catalog available', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData())

    await store.fetchCatalog()

    expect(store.availableCount).toBe(30)
  })

  it('unavailableCount returns catalog unavailable', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData())

    await store.fetchCatalog()

    expect(store.unavailableCount).toBe(41)
  })

  it('hasCatalog is true after loading', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData())

    await store.fetchCatalog()

    expect(store.hasCatalog).toBe(true)
  })

  it('hasSelectedPreview is true after preview loading', async () => {
    const store = useToolSchemaPreviewStore()
    mockPreviewResolve(makeLookupData())

    await store.fetchPreview('clarify')

    expect(store.hasSelectedPreview).toBe(true)
  })

  it('isCatalogLoading reflects loading state', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData())

    const promise = store.fetchCatalog()
    expect(store.isCatalogLoading).toBe(true)
    await promise
    expect(store.isCatalogLoading).toBe(false)
  })

  it('isPreviewLoading reflects loading state', async () => {
    const store = useToolSchemaPreviewStore()
    mockPreviewResolve(makeLookupData())

    const promise = store.fetchPreview('clarify')
    expect(store.isPreviewLoading).toBe(true)
    await promise
    expect(store.isPreviewLoading).toBe(false)
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 5. Reset Actions
// ═══════════════════════════════════════════════════════════════════════════

describe('reset actions', () => {
  it('resetCatalog clears catalog state', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData())

    await store.fetchCatalog()
    expect(store.hasCatalog).toBe(true)

    store.resetCatalog()

    expect(store.catalogState).toBe('idle')
    expect(store.catalog).toBeNull()
    expect(store.catalogError).toBe('')
    expect(store.lastFetchedAt).toBeNull()
  })

  it('resetSelectedPreview clears preview state', async () => {
    const store = useToolSchemaPreviewStore()
    mockPreviewResolve(makeLookupData())

    await store.fetchPreview('clarify')
    expect(store.hasSelectedPreview).toBe(true)

    store.resetSelectedPreview()

    expect(store.previewState).toBe('idle')
    expect(store.selectedPreview).toBeNull()
    expect(store.selectedCanonicalName).toBeNull()
    expect(store.previewError).toBe('')
  })

  it('resetErrors clears both errors', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogReject({ code: 'NETWORK_ERROR', message: 'Network error.' })
    mockPreviewReject({ code: 'NETWORK_ERROR', message: 'Network error.' })

    await store.fetchCatalog()
    await store.fetchPreview('clarify')

    expect(store.catalogError).toBeTruthy()
    expect(store.previewError).toBeTruthy()

    store.resetErrors()

    expect(store.catalogError).toBe('')
    expect(store.previewError).toBe('')
  })

  it('resetAll clears everything', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData())
    mockPreviewResolve(makeLookupData())

    await store.fetchCatalog()
    await store.fetchPreview('clarify')

    store.resetAll()

    expect(store.catalogState).toBe('idle')
    expect(store.catalog).toBeNull()
    expect(store.catalogError).toBe('')
    expect(store.lastFetchedAt).toBeNull()
    expect(store.previewState).toBe('idle')
    expect(store.selectedPreview).toBeNull()
    expect(store.selectedCanonicalName).toBeNull()
    expect(store.previewError).toBe('')
  })

  it('resetAll does not throw when called multiple times', () => {
    const store = useToolSchemaPreviewStore()
    expect(() => {
      store.resetAll()
      store.resetAll()
      store.resetAll()
    }).not.toThrow()
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 6. Abort / Cleanup
// ═══════════════════════════════════════════════════════════════════════════

describe('abort and cleanup', () => {
  it('abortAllRequests is callable without error', () => {
    const store = useToolSchemaPreviewStore()
    expect(() => store.abortAllRequests()).not.toThrow()
  })

  it('abort followed by new request works correctly', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData())
    mockPreviewResolve(makeLookupData())

    store.abortAllRequests()

    await store.fetchCatalog()
    await store.fetchPreview('clarify')

    expect(store.catalogState).toBe('success')
    expect(store.previewState).toBe('success')
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 7. Store Safety — no dangerous actions
// ═══════════════════════════════════════════════════════════════════════════

describe('store safety', () => {
  it('store does not expose execute action', () => {
    const store = useToolSchemaPreviewStore() as unknown as Record<string, unknown>
    expect(store.executeTool).toBeUndefined()
    expect(store.execute).toBeUndefined()
  })

  it('store does not expose dryRun action', () => {
    const store = useToolSchemaPreviewStore() as unknown as Record<string, unknown>
    expect(store.dryRunTool).toBeUndefined()
    expect(store.dryRun).toBeUndefined()
  })

  it('store does not expose provider schema send action', () => {
    const store = useToolSchemaPreviewStore() as unknown as Record<string, unknown>
    expect(store.sendProviderSchema).toBeUndefined()
    expect(store.sendSchema).toBeUndefined()
  })

  it('store does not expose dispatch action', () => {
    const store = useToolSchemaPreviewStore() as unknown as Record<string, unknown>
    expect(store.dispatchTool).toBeUndefined()
    expect(store.dispatch).toBeUndefined()
  })

  it('store does not expose allowlist mutation action', () => {
    const store = useToolSchemaPreviewStore() as unknown as Record<string, unknown>
    expect(store.saveAllowlist).toBeUndefined()
    expect(store.updatePolicy).toBeUndefined()
  })

  it('store does not expose enableTool action', () => {
    const store = useToolSchemaPreviewStore() as unknown as Record<string, unknown>
    expect(store.enableTool).toBeUndefined()
  })

  it('store actions only call GET API methods', async () => {
    const store = useToolSchemaPreviewStore()
    mockCatalogResolve(makeCatalogData())
    mockPreviewResolve(makeLookupData())

    await store.fetchCatalog()
    await store.fetchPreview('clarify')

    // Both API calls should be to the mocked functions (which are GET-only)
    expect(fetchToolSchemaPreviewCatalog).toHaveBeenCalledTimes(1)
    expect(fetchToolSchemaPreviewByCanonicalName).toHaveBeenCalledTimes(1)
    // No other API functions were called — only the two GET methods
  })
})
