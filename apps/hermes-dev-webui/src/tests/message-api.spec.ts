/**
 * Tests for the message API module.
 *
 * Covers URL construction, parameter encoding, and error handling.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

// ── Mock the API client ──

vi.mock('@/api/client', () => ({
  apiGet: vi.fn(),
  isDevApiError: vi.fn((err: unknown) =>
    err !== null && err !== undefined && typeof err === 'object' && 'code' in err && 'message' in err,
  ),
  getDefaultBaseUrl: vi.fn(() => 'http://127.0.0.1:5181'),
}))

import { apiGet } from '@/api/client'
import { fetchSessionMessages } from '@/api/messages'

const mockedApiGet = apiGet as unknown as ReturnType<typeof vi.fn>

// ── Test data ──

function makeMessageListData(items: Record<string, unknown>[] = [], total = 0) {
  return {
    data: {
      items,
      page: { offset: 0, limit: 50, total, hasMore: false },
    },
    meta: { requestId: 'msg-rid-1', timestamp: '2026-06-07T10:00:00Z' },
  }
}

// ── Tests ──

beforeEach(() => {
  vi.clearAllMocks()
})

describe('fetchSessionMessages', () => {
  it('calls the correct URL with sessionId', async () => {
    mockedApiGet.mockResolvedValue(makeMessageListData())
    await fetchSessionMessages('session-001')
    expect(mockedApiGet).toHaveBeenCalledOnce()
    const url = mockedApiGet.mock.calls[0]![0] as string
    expect(url).toContain('/sessions/session-001/messages')
  })

  it('encodes sessionId with special characters', async () => {
    mockedApiGet.mockResolvedValue(makeMessageListData())
    await fetchSessionMessages('session/test&id')
    const url = mockedApiGet.mock.calls[0]![0] as string
    expect(url).toContain('/sessions/session%2Ftest%26id/messages')
  })

  it('passes limit parameter', async () => {
    mockedApiGet.mockResolvedValue(makeMessageListData())
    await fetchSessionMessages('s1', { limit: 20 })
    const url = mockedApiGet.mock.calls[0]![0] as string
    expect(url).toContain('limit=20')
  })

  it('passes offset parameter', async () => {
    mockedApiGet.mockResolvedValue(makeMessageListData())
    await fetchSessionMessages('s1', { offset: 50 })
    const url = mockedApiGet.mock.calls[0]![0] as string
    expect(url).toContain('offset=50')
  })

  it('passes before anchor parameter', async () => {
    mockedApiGet.mockResolvedValue(makeMessageListData())
    await fetchSessionMessages('s1', { before: 42 })
    const url = mockedApiGet.mock.calls[0]![0] as string
    expect(url).toContain('before=42')
  })

  it('passes after anchor parameter', async () => {
    mockedApiGet.mockResolvedValue(makeMessageListData())
    await fetchSessionMessages('s1', { after: 10 })
    const url = mockedApiGet.mock.calls[0]![0] as string
    expect(url).toContain('after=10')
  })

  it('does not include default limit in query string', async () => {
    mockedApiGet.mockResolvedValue(makeMessageListData())
    await fetchSessionMessages('s1', { limit: 50 })
    const url = mockedApiGet.mock.calls[0]![0] as string
    expect(url).not.toContain('limit')
  })

  it('passes AbortSignal to apiGet', async () => {
    mockedApiGet.mockResolvedValue(makeMessageListData())
    const controller = new AbortController()
    await fetchSessionMessages('s1', {}, controller.signal)
    expect(mockedApiGet.mock.calls[0]![2]).toBe(controller.signal)
  })

  it('returns parsed response on success', async () => {
    const response = makeMessageListData([
      { id: 1, role: 'user', content: { type: 'text', text: 'Hello' }, timestamp: '2026-06-07T10:00:00Z' },
    ], 1)
    mockedApiGet.mockResolvedValue(response)
    const result = await fetchSessionMessages('s1')
    expect(result.data.items).toHaveLength(1)
  })

  it('propagates API errors', async () => {
    mockedApiGet.mockRejectedValue({
      code: 'SESSION_NOT_FOUND',
      message: 'Session was not found.',
      status: 404,
    })
    await expect(fetchSessionMessages('nonexistent')).rejects.toMatchObject({
      code: 'SESSION_NOT_FOUND',
    })
  })

  it('propagates network errors', async () => {
    mockedApiGet.mockRejectedValue({
      code: 'NETWORK_ERROR',
      message: 'Unable to connect to the API.',
    })
    await expect(fetchSessionMessages('s1')).rejects.toMatchObject({
      code: 'NETWORK_ERROR',
    })
  })
})
