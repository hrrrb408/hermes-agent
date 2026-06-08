/**
 * Tests for the Memory API, Context API, and Agent API client modules.
 *
 * Covers request construction, response parsing, error handling,
 * and query parameter building.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchMemoryStatus, fetchMemoryCategories, fetchMemoryItems, fetchMemoryItemDetail } from '@/api/memory'
import { previewContext } from '@/api/context'
import { fetchAgentStatus } from '@/api/agent'
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

function mockFetchError(error: Error): void {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error))
}

const MOCK_META = { requestId: 'test-rid', timestamp: '2026-06-08T10:00:00Z' }

beforeEach(() => {
  vi.restoreAllMocks()
})

// ── Memory API ──

describe('fetchMemoryStatus', () => {
  it('fetches memory status', async () => {
    mockFetchResponse(200, {
      data: {
        available: true,
        readOnly: true,
        rootCategories: { total: 6, active: 5, archived: 1 },
        memories: { total: 3, active: 2, archived: 1 },
        capabilities: { contextLoader: true, runtimeInjection: true, writer: true, reviewQueue: true },
        exposedCapabilities: { read: true, write: false, review: false },
      },
      meta: MOCK_META,
    })

    const result = await fetchMemoryStatus()
    expect(result.data.available).toBe(true)
    expect(result.data.readOnly).toBe(true)
    expect(result.data.rootCategories.total).toBe(6)
    expect(result.data.memories.total).toBe(3)
    expect(result.data.exposedCapabilities.write).toBe(false)
  })

  it('handles unavailable memory', async () => {
    mockFetchResponse(200, {
      data: { available: false, readOnly: true, rootCategories: { total: 0, active: 0, archived: 0 }, memories: { total: 0, active: 0, archived: 0 }, capabilities: { contextLoader: false, runtimeInjection: false, writer: false, reviewQueue: false }, exposedCapabilities: { read: false, write: false, review: false } },
      meta: MOCK_META,
    })

    const result = await fetchMemoryStatus()
    expect(result.data.available).toBe(false)
  })

  it('handles network error', async () => {
    mockFetchError(new TypeError('Failed to fetch'))

    await expect(fetchMemoryStatus()).rejects.toMatchObject({
      code: 'NETWORK_ERROR',
    })
  })
})

describe('fetchMemoryCategories', () => {
  it('fetches categories without archived', async () => {
    mockFetchResponse(200, {
      data: {
        items: [
          { key: 'hermes', title: 'Hermes', description: '...', priority: 'P0', keywords: 'hermes', status: 'active', memoryCount: 2, activeMemoryCount: 2 },
        ],
        total: 1,
      },
      meta: MOCK_META,
    })

    const result = await fetchMemoryCategories()
    expect(result.data.items).toHaveLength(1)
    expect(result.data.items[0]!.key).toBe('hermes')
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/memory/categories'),
      expect.anything(),
    )
  })

  it('includes archived when requested', async () => {
    mockFetchResponse(200, {
      data: { items: [], total: 0 },
      meta: MOCK_META,
    })

    await fetchMemoryCategories(true)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('includeArchived=true'),
      expect.anything(),
    )
  })
})

describe('fetchMemoryItems', () => {
  it('fetches items with default params', async () => {
    mockFetchResponse(200, {
      data: {
        items: [
          { id: 'MEM-TEST-001', category: 'test', title: 'Test', summary: 'Summary', tags: 'test', type: 'project_status', importance: 'P0', status: 'active', updatedAt: '2026-06-08' },
        ],
        page: { offset: 0, limit: 50, total: 1, hasMore: false },
      },
      meta: MOCK_META,
    })

    const result = await fetchMemoryItems()
    expect(result.data.items).toHaveLength(1)
    expect(result.data.page.total).toBe(1)
  })

  it('passes category filter', async () => {
    mockFetchResponse(200, {
      data: { items: [], page: { offset: 0, limit: 50, total: 0, hasMore: false } },
      meta: MOCK_META,
    })

    await fetchMemoryItems({ category: 'hermes' })
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('category=hermes'),
      expect.anything(),
    )
  })

  it('passes query filter', async () => {
    mockFetchResponse(200, {
      data: { items: [], page: { offset: 0, limit: 50, total: 0, hasMore: false } },
      meta: MOCK_META,
    })

    await fetchMemoryItems({ query: 'memory system' })
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('query=memory'),
      expect.anything(),
    )
  })

  it('handles 503 error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      headers: new Map(),
      text: () => Promise.resolve(JSON.stringify({
        error: { code: 'MEMORY_UNAVAILABLE', message: 'Memory system is unavailable.' },
        requestId: 'r1',
      })),
    }))

    await expect(fetchMemoryItems()).rejects.toMatchObject({
      code: 'MEMORY_UNAVAILABLE',
    })
  })
})

describe('fetchMemoryItemDetail', () => {
  it('fetches item detail', async () => {
    mockFetchResponse(200, {
      data: {
        id: 'MEM-TEST-001', category: 'test', title: 'Test Memory', summary: 'A test.', tags: 'test', type: 'project_status', importance: 'P0', status: 'active', createdAt: '2026-06-01', updatedAt: '2026-06-01', recordPreview: 'Full content...', truncated: false,
      },
      meta: MOCK_META,
    })

    const result = await fetchMemoryItemDetail('MEM-TEST-001')
    expect(result.data.id).toBe('MEM-TEST-001')
    expect(result.data.recordPreview).toBe('Full content...')
  })

  it('handles 404', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      headers: new Map(),
      text: () => Promise.resolve(JSON.stringify({
        error: { code: 'MEMORY_NOT_FOUND', message: 'Memory item was not found.' },
        requestId: 'r1',
      })),
    }))

    await expect(fetchMemoryItemDetail('MEM-TEST-999')).rejects.toMatchObject({
      code: 'MEMORY_NOT_FOUND',
    })
  })

  it('encodes memory ID in URL', async () => {
    mockFetchResponse(200, {
      data: { id: 'MEM-TEST-001', title: '', summary: '', tags: '', type: '', importance: '', status: '', category: '', createdAt: '', updatedAt: '', recordPreview: null, truncated: false },
      meta: MOCK_META,
    })

    await fetchMemoryItemDetail('MEM-TEST/001')
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('MEM-TEST%2F001'),
      expect.anything(),
    )
  })
})

// ── Path redaction verification ──

describe('Memory API: path redaction in responses', () => {
  it('recordPreview does not contain local paths after redaction', async () => {
    mockFetchResponse(200, {
      data: {
        id: 'MEM-TEST-001',
        category: 'test',
        title: 'Test',
        summary: 'A test.',
        tags: 'test',
        type: 'project_status',
        importance: 'P0',
        status: 'active',
        createdAt: '2026-06-01',
        updatedAt: '2026-06-01',
        recordPreview: 'Source at [local-path]. Config [file-uri-redacted]. See memory://records/test.md.',
        truncated: false,
      },
      meta: MOCK_META,
    })

    const result = await fetchMemoryItemDetail('MEM-TEST-001')
    const preview = result.data.recordPreview ?? ''
    // Redaction markers should be present
    expect(preview).toContain('[local-path]')
    expect(preview).toContain('[file-uri-redacted]')
    // Raw local paths must NOT appear
    expect(preview).not.toContain('/Users/')
    expect(preview).not.toContain('/home/')
    expect(preview).not.toContain('file://')
    // memory:// references are preserved
    expect(preview).toContain('memory://')
  })

  it('recordPreview with null value is handled safely', async () => {
    mockFetchResponse(200, {
      data: {
        id: 'MEM-TEST-002',
        category: 'test',
        title: 'No Preview',
        summary: '',
        tags: '',
        type: '',
        importance: '',
        status: 'active',
        createdAt: '',
        updatedAt: '',
        recordPreview: null,
        truncated: false,
      },
      meta: MOCK_META,
    })

    const result = await fetchMemoryItemDetail('MEM-TEST-002')
    expect(result.data.recordPreview).toBeNull()
  })

  it('recordPreview with only safe content passes through', async () => {
    mockFetchResponse(200, {
      data: {
        id: 'MEM-TEST-003',
        category: 'test',
        title: 'Safe Content',
        summary: '',
        tags: '',
        type: '',
        importance: '',
        status: 'active',
        createdAt: '',
        updatedAt: '',
        recordPreview: 'This is safe content with https://example.com and memory://ref.',
        truncated: false,
      },
      meta: MOCK_META,
    })

    const result = await fetchMemoryItemDetail('MEM-TEST-003')
    const preview = result.data.recordPreview ?? ''
    expect(preview).toContain('https://example.com')
    expect(preview).toContain('memory://ref')
    expect(preview).not.toContain('/Users/')
    expect(preview).not.toContain('/home/')
    expect(preview).not.toContain('file://')
  })
})

// ── Context API ──

describe('previewContext', () => {
  it('sends POST request with query', async () => {
    mockFetchResponse(200, {
      data: {
        query: 'test query',
        matchedCategories: [],
        memories: [],
        limits: { maxCategories: 3, maxMemories: 5, maxRecordChars: 3000 },
        sideEffects: false,
      },
      meta: MOCK_META,
    })

    const result = await previewContext({ query: 'test query' })
    expect(result.data.sideEffects).toBe(false)

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/context/preview'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('includes options in request body', async () => {
    mockFetchResponse(200, {
      data: {
        query: 'test',
        matchedCategories: [],
        memories: [],
        limits: { maxCategories: 1, maxMemories: 2, maxRecordChars: 100 },
        sideEffects: false,
      },
      meta: MOCK_META,
    })

    await previewContext({
      query: 'test',
      options: { maxCategories: 1, maxMemories: 2, maxRecordChars: 100 },
    })

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    const rawBody = callArgs[1].body
    const body = JSON.parse(typeof rawBody === 'string' ? rawBody : '{}')
    expect(body.options.maxCategories).toBe(1)
    expect(body.options.maxMemories).toBe(2)
  })

  it('handles 400 validation error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: new Map(),
      text: () => Promise.resolve(JSON.stringify({
        error: { code: 'INVALID_PARAMETER', message: 'Query is required.' },
        requestId: 'r1',
      })),
    }))

    await expect(previewContext({ query: '' })).rejects.toMatchObject({
      code: 'INVALID_PARAMETER',
    })
  })
})

// ── Agent API ──

describe('fetchAgentStatus', () => {
  it('fetches agent status', async () => {
    mockFetchResponse(200, {
      data: {
        available: true,
        readOnly: true,
        runtime: { entry: 'conversation_loop', messageSendEnabled: false, streamingEnabled: false, toolExecutionEnabled: false },
        model: { configured: true, provider: 'OpenAI', name: 'gpt-4' },
        memory: { enabled: true, contextLoaderEnabled: true, autoWriteEnabled: false, reviewQueueEnabled: false },
      },
      meta: MOCK_META,
    })

    const result = await fetchAgentStatus()
    expect(result.data.available).toBe(true)
    expect(result.data.readOnly).toBe(true)
    expect(result.data.runtime.toolExecutionEnabled).toBe(false)
    expect(result.data.memory.autoWriteEnabled).toBe(false)
  })

  it('handles unavailable agent', async () => {
    mockFetchResponse(200, {
      data: {
        available: false,
        readOnly: true,
        runtime: { entry: 'conversation_loop', messageSendEnabled: false, streamingEnabled: false, toolExecutionEnabled: false },
        model: { configured: false, provider: '', name: '' },
        memory: { enabled: false, contextLoaderEnabled: false, autoWriteEnabled: false, reviewQueueEnabled: false },
      },
      meta: MOCK_META,
    })

    const result = await fetchAgentStatus()
    expect(result.data.available).toBe(false)
  })
})

// ── Client export verification ──

describe('API client exports', () => {
  it('isDevApiError identifies error objects', () => {
    expect(isDevApiError({ code: 'TEST', message: 'test' })).toBe(true)
    expect(isDevApiError(null)).toBe(false)
    expect(isDevApiError({})).toBe(false)
    expect(isDevApiError('error')).toBe(false)
  })
})
