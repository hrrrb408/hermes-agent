/**
 * Tests for the Tool Schema Preview API client module.
 *
 * Covers:
 * - GET /tools/schemas — catalog request construction, response parsing
 * - GET /tools/schemas/{canonicalName} — URL encoding, response parsing
 * - AbortSignal passing
 * - Error handling (200, 404, 500, network error)
 * - No dangerous parameters sent
 * - No POST/PUT/PATCH/DELETE
 * - No request body
 * - No external URLs
 * - No provider/execute/dry-run/dispatch endpoints
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  fetchToolSchemaPreviewCatalog,
  fetchToolSchemaPreviewByCanonicalName,
} from '@/api/toolSchemaPreview'
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

const MOCK_META = { requestId: 'test-rid', timestamp: '2026-06-11T10:00:00Z' }

/** Minimal valid catalog item. */
const MOCK_CATALOG_ITEM = {
  canonicalName: 'clarify',
  risk: 'R0',
  capabilities: ['PURE_COMPUTE'],
  schemaPreviewAvailable: true,
  schemaShape: 'object',
  inputFields: [
    {
      fieldName: 'query',
      fieldType: 'string',
      required: true,
      descriptionPreview: 'The clarification question.',
      enumPreview: null,
      defaultPresence: false,
      constraintsPreview: null,
    },
  ],
  redactionStatus: 'clean',
  reasonCode: 'AVAILABLE',
  unavailableReason: null,
}

/** Minimal valid catalog response data. */
const MOCK_CATALOG_DATA = {
  totalCount: 71,
  availableCount: 30,
  unavailableCount: 41,
  items: [MOCK_CATALOG_ITEM],
}

/** Minimal valid lookup response data. */
const MOCK_LOOKUP_DATA = {
  found: true,
  preview: MOCK_CATALOG_ITEM,
  reasonCode: 'FOUND',
}

beforeEach(() => {
  vi.restoreAllMocks()
})

// ═══════════════════════════════════════════════════════════════════════════
// 1. fetchToolSchemaPreviewCatalog
// ═══════════════════════════════════════════════════════════════════════════

describe('fetchToolSchemaPreviewCatalog', () => {
  it('makes GET request', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolSchemaPreviewCatalog()

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    expect(callArgs[1].method).toBe('GET')
  })

  it('uses correct URL', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolSchemaPreviewCatalog()

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('/api/dev/v1/tools/schemas')
  })

  it('does not send request body', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolSchemaPreviewCatalog()

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    expect(callArgs[1].body).toBeUndefined()
  })

  it('passes AbortSignal through combined signal', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })
    const controller = new AbortController()

    await fetchToolSchemaPreviewCatalog(controller.signal)

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    const receivedSignal = callArgs[1].signal
    expect(receivedSignal).toBeDefined()
    expect(receivedSignal!.aborted).toBe(false)
  })

  it('correctly parses catalog response', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    const result = await fetchToolSchemaPreviewCatalog()

    expect(result.data.totalCount).toBe(71)
    expect(result.data.availableCount).toBe(30)
    expect(result.data.unavailableCount).toBe(41)
    expect(result.data.items).toHaveLength(1)
    expect(result.data.items[0]?.canonicalName).toBe('clarify')
    expect(result.data.items[0]?.schemaPreviewAvailable).toBe(true)
    expect(result.data.items[0]?.inputFields).toHaveLength(1)
    expect(result.data.items[0]?.redactionStatus).toBe('clean')
    expect(result.meta.requestId).toBe('test-rid')
  })

  it('handles HTTP 500 error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      headers: new Map(),
      text: () => Promise.resolve(JSON.stringify({
        error: { code: 'INTERNAL_ERROR', message: 'Internal server error.' },
        requestId: 'err-rid',
      })),
    }))

    await expect(fetchToolSchemaPreviewCatalog()).rejects.toMatchObject({
      code: 'INTERNAL_ERROR',
    })
  })

  it('handles network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(fetchToolSchemaPreviewCatalog()).rejects.toMatchObject({
      code: 'NETWORK_ERROR',
    })
  })

  it('handles AbortError correctly', async () => {
    const controller = new AbortController()
    controller.abort()

    try {
      await fetchToolSchemaPreviewCatalog(controller.signal)
      expect.fail('Should have thrown')
    } catch (err) {
      expect(isDevApiError(err)).toBe(true)
      expect((err as { code: string }).code).toBe('REQUEST_CANCELLED')
    }
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 2. fetchToolSchemaPreviewByCanonicalName
// ═══════════════════════════════════════════════════════════════════════════

describe('fetchToolSchemaPreviewByCanonicalName', () => {
  it('makes GET request', async () => {
    mockFetchResponse(200, { data: MOCK_LOOKUP_DATA, meta: MOCK_META })

    await fetchToolSchemaPreviewByCanonicalName('clarify')

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    expect(callArgs[1].method).toBe('GET')
  })

  it('uses correct URL with canonical name', async () => {
    mockFetchResponse(200, { data: MOCK_LOOKUP_DATA, meta: MOCK_META })

    await fetchToolSchemaPreviewByCanonicalName('clarify')

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('/api/dev/v1/tools/schemas/clarify')
  })

  it('URL-encodes canonical name', async () => {
    mockFetchResponse(200, { data: MOCK_LOOKUP_DATA, meta: MOCK_META })

    await fetchToolSchemaPreviewByCanonicalName('web_search')

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('/api/dev/v1/tools/schemas/web_search')
  })

  it('URL-encodes special characters in canonical name', async () => {
    mockFetchResponse(200, { data: MOCK_LOOKUP_DATA, meta: MOCK_META })

    await fetchToolSchemaPreviewByCanonicalName('tool name & more')

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('tool%20name%20%26%20more')
  })

  it('does not send request body', async () => {
    mockFetchResponse(200, { data: MOCK_LOOKUP_DATA, meta: MOCK_META })

    await fetchToolSchemaPreviewByCanonicalName('clarify')

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    expect(callArgs[1].body).toBeUndefined()
  })

  it('correctly parses lookup response', async () => {
    mockFetchResponse(200, { data: MOCK_LOOKUP_DATA, meta: MOCK_META })

    const result = await fetchToolSchemaPreviewByCanonicalName('clarify')

    expect(result.data.found).toBe(true)
    expect(result.data.reasonCode).toBe('FOUND')
    expect(result.data.preview).not.toBeNull()
    expect(result.data.preview!.canonicalName).toBe('clarify')
    expect(result.data.preview!.schemaPreviewAvailable).toBe(true)
  })

  it('handles 404 not found', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      headers: new Map(),
      text: () => Promise.resolve(JSON.stringify({
        error: {
          code: 'TOOL_SCHEMA_PREVIEW_NOT_FOUND',
          message: "Tool schema preview not found for 'nonexistent'.",
        },
        requestId: 'err-rid',
      })),
    }))

    await expect(fetchToolSchemaPreviewByCanonicalName('nonexistent')).rejects.toMatchObject({
      code: 'TOOL_SCHEMA_PREVIEW_NOT_FOUND',
    })
  })

  it('handles HTTP 500 error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      headers: new Map(),
      text: () => Promise.resolve(JSON.stringify({
        error: { code: 'INTERNAL_ERROR', message: 'Internal server error.' },
        requestId: 'err-rid',
      })),
    }))

    await expect(fetchToolSchemaPreviewByCanonicalName('clarify')).rejects.toMatchObject({
      code: 'INTERNAL_ERROR',
    })
  })

  it('handles network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(fetchToolSchemaPreviewByCanonicalName('clarify')).rejects.toMatchObject({
      code: 'NETWORK_ERROR',
    })
  })

  it('handles AbortError correctly', async () => {
    const controller = new AbortController()
    controller.abort()

    try {
      await fetchToolSchemaPreviewByCanonicalName('clarify', controller.signal)
      expect.fail('Should have thrown')
    } catch (err) {
      expect(isDevApiError(err)).toBe(true)
      expect((err as { code: string }).code).toBe('REQUEST_CANCELLED')
    }
  })

  it('passes AbortSignal through combined signal', async () => {
    mockFetchResponse(200, { data: MOCK_LOOKUP_DATA, meta: MOCK_META })
    const controller = new AbortController()

    await fetchToolSchemaPreviewByCanonicalName('clarify', controller.signal)

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    const receivedSignal = callArgs[1].signal
    expect(receivedSignal).toBeDefined()
    expect(receivedSignal!.aborted).toBe(false)
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// 3. Network Safety — no dangerous methods or endpoints
// ═══════════════════════════════════════════════════════════════════════════

describe('network safety', () => {
  it('catalog request URL contains only schema preview path', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolSchemaPreviewCatalog()

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('/api/dev/v1/tools/schemas')
    expect(url).not.toContain('/execute')
    expect(url).not.toContain('/dry-run')
    expect(url).not.toContain('/provider')
    expect(url).not.toContain('/dispatch')
    expect(url).not.toContain('/audit')
  })

  it('lookup request URL contains only schema preview path', async () => {
    mockFetchResponse(200, { data: MOCK_LOOKUP_DATA, meta: MOCK_META })

    await fetchToolSchemaPreviewByCanonicalName('clarify')

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    expect(url).toContain('/api/dev/v1/tools/schemas/clarify')
    expect(url).not.toContain('/execute')
    expect(url).not.toContain('/dry-run')
    expect(url).not.toContain('/provider')
    expect(url).not.toContain('/dispatch')
    expect(url).not.toContain('/audit')
  })

  it('no request uses external domains', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolSchemaPreviewCatalog()

    const url = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[0] as string
    // The base URL is 127.0.0.1 — no external domains
    expect(url).toContain('127.0.0.1')
    expect(url).not.toContain('api.openai.com')
    expect(url).not.toContain('api.anthropic.com')
    expect(url).not.toContain('.provider.')
  })

  it('catalog request does not send POST/PUT/PATCH/DELETE', async () => {
    mockFetchResponse(200, { data: MOCK_CATALOG_DATA, meta: MOCK_META })

    await fetchToolSchemaPreviewCatalog()

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    expect(callArgs[1].method).toBe('GET')
    expect(callArgs[1].method).not.toBe('POST')
    expect(callArgs[1].method).not.toBe('PUT')
    expect(callArgs[1].method).not.toBe('PATCH')
    expect(callArgs[1].method).not.toBe('DELETE')
  })

  it('lookup request does not send POST/PUT/PATCH/DELETE', async () => {
    mockFetchResponse(200, { data: MOCK_LOOKUP_DATA, meta: MOCK_META })

    await fetchToolSchemaPreviewByCanonicalName('clarify')

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    expect(callArgs[1].method).toBe('GET')
    expect(callArgs[1].method).not.toBe('POST')
    expect(callArgs[1].method).not.toBe('PUT')
    expect(callArgs[1].method).not.toBe('PATCH')
    expect(callArgs[1].method).not.toBe('DELETE')
  })
})
