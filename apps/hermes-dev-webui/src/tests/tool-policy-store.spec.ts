/**
 * Tests for the Tool Policy Pinia store.
 *
 * Covers:
 * - Initial state
 * - Policy loading (success, error, abort, race)
 * - Catalog loading (success, error, abort, race)
 * - Filter state (setQuery, setRisk, setCapability, setPolicyStatus, setPage, setPageSize, setSort)
 * - Selection (selectTool, clearSelection, stale selection cleanup)
 * - Safety invariants (policy and catalog violations)
 * - Retry
 * - Reset / cleanup
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import { useToolPolicyStore } from '@/stores/toolPolicy'

// ── Mock the API module ──

vi.mock('@/api/toolPolicy', () => ({
  fetchToolPolicyStatus: vi.fn(),
  fetchToolCatalog: vi.fn(),
}))

import { fetchToolPolicyStatus, fetchToolCatalog } from '@/api/toolPolicy'

// ── Test data factories ──

function makePolicyData(overrides: Record<string, unknown> = {}) {
  return {
    mode: 'DEFAULT_DENY',
    inventoryCount: 71,
    riskCounts: { R0: 1, R1: 5, R2: 19, R3: 26, R4: 17, R5: 3 },
    permanentDenylistCount: 26,
    candidateAllowlistCount: 6,
    enabledAllowlistCount: 0,
    execution: {
      implemented: false,
      enabled: false,
      providerSchemaSent: false,
      dispatchAvailable: false,
      auditAvailable: false,
    },
    limits: {
      maxArgumentPayloadBytes: 65536,
      maxArgumentNestingDepth: 8,
      maxArgumentStringLength: 32768,
      maxArgumentArrayLength: 256,
      defaultR0TimeoutSeconds: 30,
      defaultR1TimeoutSeconds: 60,
      maxToolTimeoutSeconds: 300,
      maxToolCallsPerRun: 50,
      maxGlobalConcurrency: 10,
      maxConcurrencyPerRun: 5,
      maxSerializedOutputBytes: 1048576,
      maxAgentVisibleOutputBytes: 524288,
      maxWebPreviewOutputBytes: 65536,
    },
    safety: {
      readOnly: true,
      sideEffects: false,
      writeEnabled: false,
      executeAvailable: false,
      policyMutationAvailable: false,
    },
    ...overrides,
  }
}

function makeCatalogItem(overrides: Record<string, unknown> = {}) {
  return {
    canonicalName: 'clarify',
    primaryRisk: 'R0' as const,
    riskRank: '0',
    capabilities: ['PURE_COMPUTE'] as const,
    permanentlyDenied: false,
    candidateAllowlisted: false,
    staticallyAllowed: false,
    allowed: false,
    policyStatus: 'UNLISTED' as const,
    reasonCode: 'TOOL_NOT_ALLOWED',
    sourceModule: 'tools/clarify.py',
    rationalePreview: 'Pure computation.',
    executionAvailable: false,
    schemaPreviewAvailable: false,
    dryRunAvailable: false,
    ...overrides,
  }
}

function makeCatalogData(overrides: Record<string, unknown> = {}) {
  return {
    items: [makeCatalogItem()],
    page: 1,
    pageSize: 25,
    total: 1,
    totalPages: 1,
    filters: {
      q: null,
      risk: null,
      capability: null,
      policyStatus: null,
      sort: 'nameAsc',
    },
    summary: {
      inventoryCount: 71,
      permanentDenylistCount: 26,
      candidateAllowlistCount: 6,
      enabledAllowlistCount: 0,
    },
    safety: {
      readOnly: true,
      sideEffects: false,
      executeAvailable: false,
    },
    ...overrides,
  }
}

const MOCK_META = { requestId: 'test-rid', timestamp: '2026-06-10T10:00:00Z' }

function mockPolicyResolve(data: Record<string, unknown>) {
  return (fetchToolPolicyStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
    data,
    meta: MOCK_META,
  })
}

function mockCatalogResolve(data: Record<string, unknown>) {
  return (fetchToolCatalog as ReturnType<typeof vi.fn>).mockResolvedValue({
    data,
    meta: MOCK_META,
  })
}

function mockPolicyReject(err: unknown) {
  return (fetchToolPolicyStatus as ReturnType<typeof vi.fn>).mockRejectedValue(err)
}

function mockCatalogReject(err: unknown) {
  return (fetchToolCatalog as ReturnType<typeof vi.fn>).mockRejectedValue(err)
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

// ═══════════════════════════════════════════════════════════════════════════
// 1. Initial State
// ═══════════════════════════════════════════════════════════════════════════

describe('initial state', () => {
  it('has default activeSubTab "overview"', () => {
    const store = useToolPolicyStore()
    expect(store.activeSubTab).toBe('overview')
  })

  it('policy state is idle', () => {
    const store = useToolPolicyStore()
    expect(store.policyState).toBe('idle')
  })

  it('catalog state is idle', () => {
    const store = useToolPolicyStore()
    expect(store.catalogState).toBe('idle')
  })

  it('policy is null', () => {
    const store = useToolPolicyStore()
    expect(store.policy).toBeNull()
  })

  it('catalog is null', () => {
    const store = useToolPolicyStore()
    expect(store.catalog).toBeNull()
  })

  it('selectedToolName is null', () => {
    const store = useToolPolicyStore()
    expect(store.selectedToolName).toBeNull()
  })

  it('default filters have correct values', () => {
    const store = useToolPolicyStore()
    expect(store.filters.q).toBe('')
    expect(store.filters.risk).toBeUndefined()
    expect(store.filters.capability).toBeUndefined()
    expect(store.filters.policyStatus).toBeUndefined()
    expect(store.filters.page).toBe(1)
    expect(store.filters.pageSize).toBe(25)
    expect(store.filters.sort).toBe('nameAsc')
  })

  it('no errors', () => {
    const store = useToolPolicyStore()
    expect(store.policyError).toBe('')
    expect(store.catalogError).toBe('')
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 2. Policy Loading
// ═══════════════════════════════════════════════════════════════════════════

describe('loadPolicy', () => {
  it('transitions idle → loading → success', async () => {
    const store = useToolPolicyStore()
    mockPolicyResolve(makePolicyData())

    const promise = store.loadPolicy()
    expect(store.policyState).toBe('loading')
    await promise
    expect(store.policyState).toBe('success')
  })

  it('saves policy data', async () => {
    const store = useToolPolicyStore()
    const data = makePolicyData()
    mockPolicyResolve(data)

    await store.loadPolicy()

    expect(store.policy).not.toBeNull()
    expect(store.policy!.mode).toBe('DEFAULT_DENY')
    expect(store.policy!.inventoryCount).toBe(71)
  })

  it('transitions to error on failure', async () => {
    const store = useToolPolicyStore()
    mockPolicyReject({ code: 'NETWORK_ERROR', message: 'Network error.' })

    await store.loadPolicy()

    expect(store.policyState).toBe('error')
    expect(store.policyError).toBe('Network error.')
  })

  it('does not enter error on abort', async () => {
    const store = useToolPolicyStore()
    mockPolicyReject({ code: 'REQUEST_CANCELLED', message: 'Cancelled.' })

    await store.loadPolicy()

    expect(store.policyState).toBe('loading')
    expect(store.policyError).toBe('')
  })

  it('new request cancels old request', async () => {
    const store = useToolPolicyStore()
    mockPolicyResolve(makePolicyData())

    // Start first load but don't await
    store.loadPolicy()
    // Start second load (cancels first)
    await store.loadPolicy()

    // Only the second call's result should be stored
    expect(store.policyState).toBe('success')
    expect(fetchToolPolicyStatus).toHaveBeenCalledTimes(2)
  })

  it('stale policy response does not overwrite new response', async () => {
    const store = useToolPolicyStore()
    const firstData = makePolicyData({ inventoryCount: 10 })
    const secondData = makePolicyData({ inventoryCount: 20 })

    let firstResolve: (value: unknown) => void
    const firstPromise = new Promise(resolve => { firstResolve = resolve })

    ;(fetchToolPolicyStatus as ReturnType<typeof vi.fn>)
      .mockImplementationOnce(() => firstPromise)
      .mockImplementationOnce(() => Promise.resolve({ data: secondData, meta: MOCK_META }))

    // Start first request
    store.loadPolicy()
    // Start second request
    const secondDone = store.loadPolicy()

    // Second request completes
    await secondDone
    expect(store.policy!.inventoryCount).toBe(20)

    // First request resolves late
    firstResolve!({ data: firstData, meta: MOCK_META })
    await new Promise(r => setTimeout(r, 10))

    // Data should still be from the second request
    expect(store.policy!.inventoryCount).toBe(20)
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 3. Catalog Loading
// ═══════════════════════════════════════════════════════════════════════════

describe('loadCatalog', () => {
  it('transitions idle → loading → success', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData())

    const promise = store.loadCatalog()
    expect(store.catalogState).toBe('loading')
    await promise
    expect(store.catalogState).toBe('success')
  })

  it('passes current filters to API', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData())

    store.setQuery('memory')
    store.setRisk('R1')
    await store.loadCatalog()

    expect(fetchToolCatalog).toHaveBeenCalledWith(
      expect.objectContaining({ q: 'memory', risk: 'R1', page: 1 }),
      expect.any(AbortSignal),
    )
  })

  it('saves catalog data', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData())

    await store.loadCatalog()

    expect(store.catalog).not.toBeNull()
    expect(store.catalog!.total).toBe(1)
    expect(store.catalogItems).toHaveLength(1)
  })

  it('transitions to error on failure', async () => {
    const store = useToolPolicyStore()
    mockCatalogReject({ code: 'INVALID_TOOL_RISK', message: 'Invalid risk.' })

    await store.loadCatalog()

    expect(store.catalogState).toBe('error')
    expect(store.catalogError).toBe('Invalid risk.')
  })

  it('does not enter error on abort', async () => {
    const store = useToolPolicyStore()
    mockCatalogReject({ code: 'REQUEST_CANCELLED', message: 'Cancelled.' })

    await store.loadCatalog()

    expect(store.catalogState).toBe('loading')
    expect(store.catalogError).toBe('')
  })

  it('stale catalog response does not overwrite new response', async () => {
    const store = useToolPolicyStore()
    const firstData = makeCatalogData({ total: 5 })
    const secondData = makeCatalogData({ total: 10 })

    let firstResolve: (value: unknown) => void
    const firstPromise = new Promise(resolve => { firstResolve = resolve })

    ;(fetchToolCatalog as ReturnType<typeof vi.fn>)
      .mockImplementationOnce(() => firstPromise)
      .mockImplementationOnce(() => Promise.resolve({ data: secondData, meta: MOCK_META }))

    store.loadCatalog()
    const secondDone = store.loadCatalog()

    await secondDone
    expect(store.catalog!.total).toBe(10)

    firstResolve!({ data: firstData, meta: MOCK_META })
    await new Promise(r => setTimeout(r, 10))

    expect(store.catalog!.total).toBe(10)
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 4. Retry
// ═══════════════════════════════════════════════════════════════════════════

describe('retry', () => {
  it('retryPolicy reloads policy', async () => {
    const store = useToolPolicyStore()
    mockPolicyResolve(makePolicyData())

    await store.loadPolicy()
    store.retryPolicy()

    expect(fetchToolPolicyStatus).toHaveBeenCalledTimes(2)
  })

  it('retryCatalog reloads with current filters', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData())

    store.setQuery('file')
    await store.loadCatalog()
    store.retryCatalog()

    expect(fetchToolCatalog).toHaveBeenCalledTimes(2)
    // Second call should still have the 'file' filter
    const calls = (fetchToolCatalog as ReturnType<typeof vi.fn>).mock.calls
    const lastCall = calls[1]!
    expect(lastCall[0].q).toBe('file')
  })

  it('retry does not clear filters', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData())

    store.setQuery('memory')
    store.setRisk('R2')
    await store.loadCatalog()
    store.retryCatalog()

    expect(store.filters.q).toBe('memory')
    expect(store.filters.risk).toBe('R2')
  })

  it('retry does not change page', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData())

    store.setPage(3)
    await store.loadCatalog()
    store.retryCatalog()

    expect(store.filters.page).toBe(3)
  })

  it('retry does not clear selection', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData())

    await store.loadCatalog()
    store.selectTool('clarify')
    store.retryCatalog()

    expect(store.selectedToolName).toBe('clarify')
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 5. Filters
// ═══════════════════════════════════════════════════════════════════════════

describe('filters', () => {
  it('setQuery resets page to 1', () => {
    const store = useToolPolicyStore()
    store.setPage(5)
    store.setQuery('memory')
    expect(store.filters.page).toBe(1)
    expect(store.filters.q).toBe('memory')
  })

  it('setRisk resets page to 1', () => {
    const store = useToolPolicyStore()
    store.setPage(5)
    store.setRisk('R3')
    expect(store.filters.page).toBe(1)
    expect(store.filters.risk).toBe('R3')
  })

  it('setCapability resets page to 1', () => {
    const store = useToolPolicyStore()
    store.setPage(5)
    store.setCapability('PURE_COMPUTE')
    expect(store.filters.page).toBe(1)
    expect(store.filters.capability).toBe('PURE_COMPUTE')
  })

  it('setPolicyStatus resets page to 1', () => {
    const store = useToolPolicyStore()
    store.setPage(5)
    store.setPolicyStatus('PERMANENTLY_DENIED')
    expect(store.filters.page).toBe(1)
    expect(store.filters.policyStatus).toBe('PERMANENTLY_DENIED')
  })

  it('setPage sets correct value', () => {
    const store = useToolPolicyStore()
    store.setPage(3)
    expect(store.filters.page).toBe(3)
  })

  it('setPage rejects values less than 1', () => {
    const store = useToolPolicyStore()
    store.setPage(0)
    expect(store.filters.page).toBe(1)
  })

  it('setPage rejects negative values', () => {
    const store = useToolPolicyStore()
    store.setPage(-5)
    expect(store.filters.page).toBe(1)
  })

  it('setPageSize clamps to 1–100', () => {
    const store = useToolPolicyStore()
    store.setPageSize(50)
    expect(store.filters.pageSize).toBe(50)

    store.setPageSize(0)
    expect(store.filters.pageSize).toBe(1)

    store.setPageSize(200)
    expect(store.filters.pageSize).toBe(100)
  })

  it('setPageSize resets page to 1', () => {
    const store = useToolPolicyStore()
    store.setPage(5)
    store.setPageSize(10)
    expect(store.filters.page).toBe(1)
  })

  it('setSort resets page to 1', () => {
    const store = useToolPolicyStore()
    store.setPage(5)
    store.setSort('riskDesc')
    expect(store.filters.page).toBe(1)
    expect(store.filters.sort).toBe('riskDesc')
  })

  it('clearing filter by setting undefined', () => {
    const store = useToolPolicyStore()
    store.setRisk('R3')
    expect(store.filters.risk).toBe('R3')

    store.setRisk(undefined)
    expect(store.filters.risk).toBeUndefined()
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 6. Selection
// ═══════════════════════════════════════════════════════════════════════════

describe('selection', () => {
  it('selectTool saves canonical name', () => {
    const store = useToolPolicyStore()
    store.selectTool('terminal')
    expect(store.selectedToolName).toBe('terminal')
  })

  it('selectedTool computed returns matching item', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData())

    await store.loadCatalog()
    store.selectTool('clarify')

    expect(store.selectedTool).not.toBeNull()
    expect(store.selectedTool!.canonicalName).toBe('clarify')
  })

  it('selectedTool returns null when no match', () => {
    const store = useToolPolicyStore()
    store.selectTool('nonexistent')
    expect(store.selectedTool).toBeNull()
  })

  it('clearSelection clears name', () => {
    const store = useToolPolicyStore()
    store.selectTool('terminal')
    store.clearSelection()
    expect(store.selectedToolName).toBeNull()
  })

  it('selection preserved when tool remains in new catalog', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData())

    await store.loadCatalog()
    store.selectTool('clarify')

    // Reload same catalog
    mockCatalogResolve(makeCatalogData())
    await store.loadCatalog()

    expect(store.selectedToolName).toBe('clarify')
  })

  it('selection cleared when tool removed from new catalog', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData())
    await store.loadCatalog()
    store.selectTool('clarify')

    // Reload with different items
    mockCatalogResolve(makeCatalogData({
      items: [makeCatalogItem({ canonicalName: 'other_tool' })],
    }))
    await store.loadCatalog()

    expect(store.selectedToolName).toBeNull()
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 7. Safety Invariants — Policy
// ═══════════════════════════════════════════════════════════════════════════

describe('safety invariants — policy', () => {
  it('rejects enabledAllowlistCount > 0', async () => {
    const store = useToolPolicyStore()
    mockPolicyResolve(makePolicyData({ enabledAllowlistCount: 5 }))

    await store.loadPolicy()

    expect(store.policyState).toBe('error')
    expect(store.policyError).toContain('enabledAllowlistCount')
  })

  it('rejects execution.enabled=true', async () => {
    const store = useToolPolicyStore()
    mockPolicyResolve(makePolicyData({
      execution: {
        implemented: false,
        enabled: true,
        providerSchemaSent: false,
        dispatchAvailable: false,
        auditAvailable: false,
      },
    }))

    await store.loadPolicy()

    expect(store.policyState).toBe('error')
    expect(store.policyError).toContain('execution.enabled')
  })

  it('rejects providerSchemaSent=true', async () => {
    const store = useToolPolicyStore()
    mockPolicyResolve(makePolicyData({
      execution: {
        implemented: false,
        enabled: false,
        providerSchemaSent: true,
        dispatchAvailable: false,
        auditAvailable: false,
      },
    }))

    await store.loadPolicy()

    expect(store.policyState).toBe('error')
    expect(store.policyError).toContain('providerSchemaSent')
  })

  it('rejects dispatchAvailable=true', async () => {
    const store = useToolPolicyStore()
    mockPolicyResolve(makePolicyData({
      execution: {
        implemented: false,
        enabled: false,
        providerSchemaSent: false,
        dispatchAvailable: true,
        auditAvailable: false,
      },
    }))

    await store.loadPolicy()

    expect(store.policyState).toBe('error')
    expect(store.policyError).toContain('dispatchAvailable')
  })

  it('rejects safety.readOnly=false', async () => {
    const store = useToolPolicyStore()
    mockPolicyResolve(makePolicyData({
      safety: {
        readOnly: false,
        sideEffects: false,
        writeEnabled: false,
        executeAvailable: false,
        policyMutationAvailable: false,
      },
    }))

    await store.loadPolicy()

    expect(store.policyState).toBe('error')
    expect(store.policyError).toContain('readOnly')
  })

  it('rejects safety.sideEffects=true', async () => {
    const store = useToolPolicyStore()
    mockPolicyResolve(makePolicyData({
      safety: {
        readOnly: true,
        sideEffects: true,
        writeEnabled: false,
        executeAvailable: false,
        policyMutationAvailable: false,
      },
    }))

    await store.loadPolicy()

    expect(store.policyState).toBe('error')
    expect(store.policyError).toContain('sideEffects')
  })

  it('rejects safety.executeAvailable=true', async () => {
    const store = useToolPolicyStore()
    mockPolicyResolve(makePolicyData({
      safety: {
        readOnly: true,
        sideEffects: false,
        writeEnabled: false,
        executeAvailable: true,
        policyMutationAvailable: false,
      },
    }))

    await store.loadPolicy()

    expect(store.policyState).toBe('error')
    expect(store.policyError).toContain('executeAvailable')
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 8. Safety Invariants — Catalog
// ═══════════════════════════════════════════════════════════════════════════

describe('safety invariants — catalog', () => {
  it('rejects catalog item allowed=true', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData({
      items: [makeCatalogItem({ allowed: true })],
    }))

    await store.loadCatalog()

    expect(store.catalogState).toBe('error')
    expect(store.catalogError).toContain('allowed=true')
  })

  it('rejects catalog item executionAvailable=true', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData({
      items: [makeCatalogItem({ executionAvailable: true })],
    }))

    await store.loadCatalog()

    expect(store.catalogState).toBe('error')
    expect(store.catalogError).toContain('executionAvailable=true')
  })

  it('rejects catalog item schemaPreviewAvailable=true', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData({
      items: [makeCatalogItem({ schemaPreviewAvailable: true })],
    }))

    await store.loadCatalog()

    expect(store.catalogState).toBe('error')
    expect(store.catalogError).toContain('schemaPreviewAvailable=true')
  })

  it('rejects catalog item dryRunAvailable=true', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData({
      items: [makeCatalogItem({ dryRunAvailable: true })],
    }))

    await store.loadCatalog()

    expect(store.catalogState).toBe('error')
    expect(store.catalogError).toContain('dryRunAvailable=true')
  })

  it('rejects catalog safety.readOnly=false', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData({
      safety: { readOnly: false, sideEffects: false, executeAvailable: false },
    }))

    await store.loadCatalog()

    expect(store.catalogState).toBe('error')
    expect(store.catalogError).toContain('readOnly')
  })

  it('rejects catalog safety.sideEffects=true', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData({
      safety: { readOnly: true, sideEffects: true, executeAvailable: false },
    }))

    await store.loadCatalog()

    expect(store.catalogState).toBe('error')
    expect(store.catalogError).toContain('sideEffects')
  })

  it('rejects catalog safety.executeAvailable=true', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData({
      safety: { readOnly: true, sideEffects: false, executeAvailable: true },
    }))

    await store.loadCatalog()

    expect(store.catalogState).toBe('error')
    expect(store.catalogError).toContain('executeAvailable')
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 9. Computed / Getters
// ═══════════════════════════════════════════════════════════════════════════

describe('computed / getters', () => {
  it('isPolicyLoading reflects loading state', async () => {
    const store = useToolPolicyStore()
    mockPolicyResolve(makePolicyData())

    const promise = store.loadPolicy()
    expect(store.isPolicyLoading).toBe(true)
    await promise
    expect(store.isPolicyLoading).toBe(false)
  })

  it('isCatalogLoading reflects loading state', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData())

    const promise = store.loadCatalog()
    expect(store.isCatalogLoading).toBe(true)
    await promise
    expect(store.isCatalogLoading).toBe(false)
  })

  it('hasPolicy is false initially', () => {
    const store = useToolPolicyStore()
    expect(store.hasPolicy).toBe(false)
  })

  it('hasPolicy is true after loading', async () => {
    const store = useToolPolicyStore()
    mockPolicyResolve(makePolicyData())
    await store.loadPolicy()
    expect(store.hasPolicy).toBe(true)
  })

  it('hasCatalogResults is false initially', () => {
    const store = useToolPolicyStore()
    expect(store.hasCatalogResults).toBe(false)
  })

  it('isCatalogEmpty is true when total is 0', async () => {
    const store = useToolPolicyStore()
    mockCatalogResolve(makeCatalogData({ items: [], total: 0 }))

    await store.loadCatalog()

    expect(store.isCatalogEmpty).toBe(true)
    expect(store.hasCatalogResults).toBe(false)
  })

  it('isReadOnly defaults to true', () => {
    const store = useToolPolicyStore()
    expect(store.isReadOnly).toBe(true)
  })

  it('isExecutionAvailable defaults to false', () => {
    const store = useToolPolicyStore()
    expect(store.isExecutionAvailable).toBe(false)
  })

  it('catalogItems returns empty array before load', () => {
    const store = useToolPolicyStore()
    expect(store.catalogItems).toEqual([])
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 10. Reset / Cleanup
// ═══════════════════════════════════════════════════════════════════════════

describe('reset and cleanup', () => {
  it('reset restores initial state', async () => {
    const store = useToolPolicyStore()
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())

    await store.loadPolicy()
    await store.loadCatalog()
    store.selectTool('clarify')
    store.setQuery('memory')

    store.reset()

    expect(store.activeSubTab).toBe('overview')
    expect(store.policyState).toBe('idle')
    expect(store.catalogState).toBe('idle')
    expect(store.policy).toBeNull()
    expect(store.catalog).toBeNull()
    expect(store.selectedToolName).toBeNull()
    expect(store.filters.q).toBe('')
    expect(store.filters.page).toBe(1)
    expect(store.policyError).toBe('')
    expect(store.catalogError).toBe('')
  })

  it('abortAllRequests is callable without error', () => {
    const store = useToolPolicyStore()
    // Should not throw when called without active requests
    expect(() => store.abortAllRequests()).not.toThrow()
  })

  it('abort followed by new request works correctly', async () => {
    const store = useToolPolicyStore()
    mockPolicyResolve(makePolicyData())
    mockCatalogResolve(makeCatalogData())

    store.abortAllRequests()

    await store.loadPolicy()
    await store.loadCatalog()

    expect(store.policyState).toBe('success')
    expect(store.catalogState).toBe('success')
  })
})
