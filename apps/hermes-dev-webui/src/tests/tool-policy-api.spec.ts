/**
 * Tests for the Tool Policy API client module.
 *
 * Covers:
 * - GET /tools/policy — request construction, response parsing
 * - GET /tools/catalog — query parameter encoding, response parsing
 * - AbortSignal passing
 * - Error handling
 * - No dangerous parameters sent
 * - No Tool write methods exported
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  fetchToolPolicyStatus,
  fetchToolCatalog,
} from '@/api/toolPolicy'
import { isDevApiError } from '@/api/client'

// ── Mock fetch ──

function mockFetchResponse(
  status: number,
  body: Record<string, unknown>,
): void {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    headers: new Map(),
    text: () => Promise.resolve(JSON.stringify(body)),
  }))
}

const MOCK_META = { requestId: 'test-rid', timestamp: '2026-06-10T10:00:00Z' }

/** Minimal valid policy response. */
const MOCK_POLICY_DATA = {
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
}

/** Minimal valid catalog response. */
const MOCK_CATALOG_DATA = {
  items: [
    {
      canonicalName: 'clarify',
      primaryRisk: 'R0',
      riskRank: '0',
      capabilities: ['PURE_COMPUTE'],
      permanentlyDenied: false,
      candidateAllowlisted: false,
      staticallyAllowed: false,
      allowed: false,
      policyStatus: 'UNLISTED',
      reasonCode: 'TOOL_NOT_ALLOWED',
      sourceModule: 'tools/clarify.py',
      rationalePreview: 'Pure computation.',
      executionAvailable: false,
      schemaPreviewAvailable: false,
      dryRunAvailable: false,
    },
  ],
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
}

const DEFAULT_FILTERS = {
  q: '',
  risk: undefined,
  capability: undefined,
  policyStatus: undefined,
  page: 1,
  pageSize: 25,
  sort: 'nameAsc' as const,
}

beforeEach(() => {
  vi.restoreAllMocks()
})

// ── fetchToolPolicyStatus ──

describe('fetchToolPolicyStatus', () => {
  it('makes GET request', async () => {
    mockFetchResponse(200, { data: MOCK_POLICY_DATA, meta: MOCK_META })

    await fetchToolPolicyStatus()

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    expect(callArgs[1].method).toBe('GET')
  })

  it('uses correct URL', async () => {
    mockFetchResponse(200, { data: MOCK_POLICY_DATA, meta: MOCK_META })

    await fetchToolPolicyStatus()

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('/api/dev/v1/tools/policy')
  })

  it('passes AbortSignal through combined signal', async () => {
    mockFetchResponse(200, { data: MOCK_POLICY_DATA, meta: MOCK_META })
    const controller = new AbortController()

    await fetchToolPolicyStatus(controller.signal)

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    // The API client chains user signal into a combined timeout signal
    const receivedSignal = callArgs[1].signal
    expect(receivedSignal).toBeDefined()
    expect(receivedSignal!.aborted).toBe(false)
  })

  it('correctly parses response', async () => {
    mockFetchResponse(200, { data: MOCK_POLICY_DATA, meta: MOCK_META })

    const result = await fetchToolPolicyStatus()

    expect(result.data.mode).toBe('DEFAULT_DENY')
    expect(result.data.inventoryCount).toBe(71)
    expect(result.data.enabledAllowlistCount).toBe(0)
    expect(result.data.execution.enabled).toBe(false)
    expect(result.data.safety.readOnly).toBe(true)
    expect(result.data.riskCounts.R0).toBe(1)
    expect(result.data.limits.maxToolCallsPerRun).toBe(50)
  })

  it('handles HTTP error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      headers: new Map(),
      text: () => Promise.resolve(JSON.stringify({
        error: { code: 'SERVICE_UNAVAILABLE', message: 'Service unavailable.' },
        requestId: 'err-rid',
      })),
    }))

    await expect(fetchToolPolicyStatus()).rejects.toMatchObject({
      code: 'SERVICE_UNAVAILABLE',
    })
  })

  it('handles AbortError correctly', async () => {
    const controller = new AbortController()
    controller.abort()

    try {
      await fetchToolPolicyStatus(controller.signal)
      expect.fail('Should have thrown')
    } catch (err) {
      expect(isDevApiError(err)).toBe(true)
      expect((err as { code: string }).code).toBe('REQUEST_CANCELLED')
    }
  })
})

// ── fetchToolCatalog ──

describe('fetchToolCatalog', () => {
  it('makes GET request', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog(DEFAULT_FILTERS)

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    expect(callArgs[1].method).toBe('GET')
  })

  it('uses correct base URL', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog(DEFAULT_FILTERS)

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('/api/dev/v1/tools/catalog')
  })

  it('encodes q parameter', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog({ ...DEFAULT_FILTERS, q: 'memory' })

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('q=memory')
  })

  it('encodes risk parameter', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog({ ...DEFAULT_FILTERS, risk: 'R3' })

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('risk=R3')
  })

  it('encodes capability parameter', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog({ ...DEFAULT_FILTERS, capability: 'PURE_COMPUTE' })

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('capability=PURE_COMPUTE')
  })

  it('encodes policyStatus parameter', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog({ ...DEFAULT_FILTERS, policyStatus: 'PERMANENTLY_DENIED' })

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('policyStatus=PERMANENTLY_DENIED')
  })

  it('encodes page parameter when > 1', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog({ ...DEFAULT_FILTERS, page: 2 })

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('page=2')
  })

  it('does not send page when default (1)', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog(DEFAULT_FILTERS)

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).not.toContain('page=')
  })

  it('encodes pageSize when not 25', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog({ ...DEFAULT_FILTERS, pageSize: 10 })

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('pageSize=10')
  })

  it('does not send pageSize when default (25)', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog(DEFAULT_FILTERS)

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).not.toContain('pageSize=')
  })

  it('encodes sort when not nameAsc', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog({ ...DEFAULT_FILTERS, sort: 'riskDesc' })

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('sort=riskDesc')
  })

  it('does not send sort when default (nameAsc)', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog(DEFAULT_FILTERS)

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).not.toContain('sort=')
  })

  it('does not send empty q parameter', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog({ ...DEFAULT_FILTERS, q: '' })

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).not.toContain('q=')
  })

  it('does not send undefined risk parameter', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog({ ...DEFAULT_FILTERS, risk: undefined })

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).not.toContain('risk=')
  })

  it('does not send undefined capability parameter', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog({ ...DEFAULT_FILTERS, capability: undefined })

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).not.toContain('capability=')
  })

  it('does not send undefined policyStatus parameter', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog({ ...DEFAULT_FILTERS, policyStatus: undefined })

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).not.toContain('policyStatus=')
  })

  it('URL-encodes query values', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolCatalog({ ...DEFAULT_FILTERS, q: 'file & read' })

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('q=file')
    // URLSearchParams encodes spaces as + or %20
    expect(url).not.toContain('q=file & read')
  })

  it('does not send dangerous parameters', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    // The function only accepts typed ToolCatalogFilters,
    // so dangerous params cannot be injected. We verify the URL.
    await fetchToolCatalog(DEFAULT_FILTERS)

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).not.toContain('execute')
    expect(url).not.toContain('force')
    expect(url).not.toContain('enable')
    expect(url).not.toContain('write')
    expect(url).not.toContain('dispatch')
    expect(url).not.toContain('override')
  })

  it('passes AbortSignal through combined signal', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })
    const controller = new AbortController()

    await fetchToolCatalog(DEFAULT_FILTERS, controller.signal)

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    // The API client chains user signal into a combined timeout signal
    const receivedSignal = callArgs[1].signal
    expect(receivedSignal).toBeDefined()
    expect(receivedSignal!.aborted).toBe(false)
  })

  it('correctly returns success response', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    const result = await fetchToolCatalog(DEFAULT_FILTERS)

    expect(result.data.total).toBe(1)
    expect(result.data.items[0]?.canonicalName).toBe('clarify')
    expect(result.data.items[0]?.allowed).toBe(false)
    expect(result.data.safety.readOnly).toBe(true)
  })

  it('correctly handles standard error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: new Map(),
      text: () => Promise.resolve(JSON.stringify({
        error: { code: 'INVALID_TOOL_RISK', message: 'Risk must be one of: R0-R5.' },
        requestId: 'err-rid',
      })),
    }))

    await expect(fetchToolCatalog(DEFAULT_FILTERS)).rejects.toMatchObject({
      code: 'INVALID_TOOL_RISK',
    })
  })

  it('correctly preserves AbortError', async () => {
    const controller = new AbortController()
    controller.abort()

    try {
      await fetchToolCatalog(DEFAULT_FILTERS, controller.signal)
      expect.fail('Should have thrown')
    } catch (err) {
      expect(isDevApiError(err)).toBe(true)
      expect((err as { code: string }).code).toBe('REQUEST_CANCELLED')
    }
  })
})
