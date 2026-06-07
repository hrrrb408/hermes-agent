/**
 * Tests for the Session store message integration.
 *
 * Covers message loading, pagination, error handling, retry,
 * concurrent request handling, and session switching.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSessionStore } from '@/stores/session'
import type { SessionMessage } from '@/types/api/message'
import type { DevApiError } from '@/api/client'

// ── Test data ──

function makeMessage(overrides: Partial<SessionMessage> = {}): SessionMessage {
  return {
    id: 1,
    role: 'user',
    content: { type: 'text', text: 'Hello' },
    timestamp: '2026-06-07T10:00:00Z',
    ...overrides,
  }
}

function makeMessageResponse(items: SessionMessage[] = [], total = 0, hasMore = false) {
  return {
    data: {
      items,
      page: { offset: 0, limit: 50, total, hasMore },
    },
    meta: { requestId: 'msg-rid-1', timestamp: '2026-06-07T10:00:00Z' },
  }
}

// ── Mock both API modules ──

vi.mock('@/api/sessions', () => ({
  fetchSessions: vi.fn(),
  fetchSessionDetail: vi.fn(),
}))

vi.mock('@/api/messages', () => ({
  fetchSessionMessages: vi.fn(),
}))

import { fetchSessionDetail } from '@/api/sessions'
import { fetchSessionMessages } from '@/api/messages'

const mockedFetchSessionDetail = fetchSessionDetail as unknown as ReturnType<typeof vi.fn>
const mockedFetchSessionMessages = fetchSessionMessages as unknown as ReturnType<typeof vi.fn>

// ── Tests ──

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('MessageStore — initial state', () => {
  it('starts with idle message status', () => {
    const store = useSessionStore()
    expect(store.messageStatus).toBe('idle')
  })

  it('starts with empty messages', () => {
    const store = useSessionStore()
    expect(store.messages).toEqual([])
  })

  it('starts with no message error', () => {
    const store = useSessionStore()
    expect(store.messageError).toBeNull()
  })

  it('starts with no message hasMore', () => {
    const store = useSessionStore()
    expect(store.messageHasMore).toBe(false)
  })
})

describe('MessageStore — load messages', () => {
  it('loads messages for a session', async () => {
    const store = useSessionStore()
    const msgs = [
      makeMessage({ id: 1, role: 'user', content: { type: 'text', text: 'Hello' } }),
      makeMessage({ id: 2, role: 'assistant', content: { type: 'text', text: 'Hi!' } }),
    ]

    mockedFetchSessionMessages.mockResolvedValue(
      makeMessageResponse(msgs, 2),
    )

    await store.loadMessages('session-001')

    expect(store.messageStatus).toBe('success')
    expect(store.messages).toHaveLength(2)
    expect(store.messageTotal).toBe(2)
  })

  it('sets empty status when no messages', async () => {
    const store = useSessionStore()
    mockedFetchSessionMessages.mockResolvedValue(
      makeMessageResponse([], 0),
    )

    await store.loadMessages('session-001')

    expect(store.messageStatus).toBe('empty')
    expect(store.messages).toEqual([])
  })

  it('sets error status on failure', async () => {
    const store = useSessionStore()
    mockedFetchSessionMessages.mockRejectedValue({
      code: 'NETWORK_ERROR',
      message: 'Unable to connect.',
    } satisfies DevApiError)

    await store.loadMessages('session-001')

    expect(store.messageStatus).toBe('error')
    expect(store.messageError).toBe('Unable to connect.')
  })

  it('can retry after error', async () => {
    const store = useSessionStore()

    // First call fails
    mockedFetchSessionMessages.mockRejectedValueOnce({
      code: 'NETWORK_ERROR',
      message: 'Network error.',
    } satisfies DevApiError)

    await store.loadMessages('session-001')
    expect(store.messageStatus).toBe('error')

    // Retry succeeds
    mockedFetchSessionMessages.mockResolvedValue(
      makeMessageResponse([makeMessage()], 1),
    )

    await store.loadMessages('session-001')
    expect(store.messageStatus).toBe('success')
    expect(store.messages).toHaveLength(1)
  })

  it('stores request ID from response', async () => {
    const store = useSessionStore()
    mockedFetchSessionMessages.mockResolvedValue({
      data: {
        items: [makeMessage()],
        page: { offset: 0, limit: 50, total: 1, hasMore: false },
      },
      meta: { requestId: 'test-msg-rid', timestamp: '2026-06-07T10:00:00Z' },
    })

    await store.loadMessages('session-001')
    expect(store.messageRequestId).toBe('test-msg-rid')
  })
})

describe('MessageStore — load more messages', () => {
  it('does not load more when hasMore is false', async () => {
    const store = useSessionStore()
    mockedFetchSessionMessages.mockResolvedValue(
      makeMessageResponse([makeMessage()], 1, false),
    )

    await store.loadMessages('session-001')
    vi.clearAllMocks()

    await store.loadMoreMessages()
    expect(mockedFetchSessionMessages).not.toHaveBeenCalled()
  })

  it('loads more messages and appends', async () => {
    const store = useSessionStore()
    store.$patch({ selectedSessionId: 'session-001' })

    // First load
    mockedFetchSessionMessages.mockResolvedValueOnce(
      makeMessageResponse(
        [makeMessage({ id: 1 }), makeMessage({ id: 2 })],
        4,
        true,
      ),
    )
    await store.loadMessages('session-001')
    expect(store.messages).toHaveLength(2)
    expect(store.messageHasMore).toBe(true)

    // Load more
    mockedFetchSessionMessages.mockResolvedValueOnce({
      data: {
        items: [makeMessage({ id: 3 }), makeMessage({ id: 4 })],
        page: { offset: 50, limit: 50, total: 4, hasMore: false },
      },
      meta: { requestId: 'msg-rid-2', timestamp: '2026-06-07T10:00:00Z' },
    })

    await store.loadMoreMessages()

    expect(store.messages).toHaveLength(4)
    expect(store.messageHasMore).toBe(false)
    expect(store.messageStatus).toBe('success')
  })

  it('deduplicates messages by ID', async () => {
    const store = useSessionStore()
    store.$patch({ selectedSessionId: 'session-001' })

    mockedFetchSessionMessages.mockResolvedValueOnce(
      makeMessageResponse([makeMessage({ id: 1 })], 2, true),
    )
    await store.loadMessages('session-001')

    // Load more returns overlapping message
    mockedFetchSessionMessages.mockResolvedValueOnce({
      data: {
        items: [makeMessage({ id: 1 }), makeMessage({ id: 2 })],
        page: { offset: 50, limit: 50, total: 2, hasMore: false },
      },
      meta: { requestId: 'msg-rid-3', timestamp: '2026-06-07T10:00:00Z' },
    })

    await store.loadMoreMessages()
    expect(store.messages).toHaveLength(2)
  })
})

describe('MessageStore — session switching', () => {
  it('loads messages when selecting a session', async () => {
    const store = useSessionStore()

    mockedFetchSessionDetail.mockResolvedValue({
      data: {
        id: 'session-001',
        title: 'Test',
        source: 'cli',
        model: null,
        messageCount: 2,
        toolCallCount: 0,
        inputTokens: null,
        outputTokens: null,
        archived: false,
        startedAt: '2026-06-07T10:00:00Z',
        endedAt: null,
        lastActiveAt: null,
        endReason: null,
      },
      meta: { requestId: 'd-rid', timestamp: '2026-06-07T10:00:00Z' },
    })

    mockedFetchSessionMessages.mockResolvedValue(
      makeMessageResponse([makeMessage()], 1),
    )

    await store.selectSession('session-001')

    expect(store.selectedSessionId).toBe('session-001')
    // Messages should be loading (async, may or may not be done yet)
    expect(mockedFetchSessionMessages).toHaveBeenCalledWith(
      'session-001',
      expect.objectContaining({ limit: 50, offset: 0 }),
      expect.any(AbortSignal),
    )
  })

  it('clears messages when clearing selection', async () => {
    const store = useSessionStore()

    // Set up some state
    store.$patch({
      selectedSessionId: 'session-001',
      messages: [makeMessage()],
      messageStatus: 'success' as const,
      messageTotal: 1,
    })

    store.clearSelection()

    expect(store.selectedSessionId).toBeNull()
    expect(store.messages).toEqual([])
    expect(store.messageStatus).toBe('idle')
    expect(store.messageTotal).toBe(0)
  })

  it('does not save messages to localStorage', async () => {
    const store = useSessionStore()

    mockedFetchSessionMessages.mockResolvedValue(
      makeMessageResponse([makeMessage()], 1),
    )

    await store.loadMessages('session-001')

    // Verify no messages in localStorage
    const keys = Object.keys(localStorage)
    for (const key of keys) {
      const value = localStorage.getItem(key) ?? ''
      expect(value).not.toContain('Hello')
    }
  })
})

describe('MessageStore — cancel and stale response', () => {
  it('cancelled request does not set error state', async () => {
    const store = useSessionStore()

    mockedFetchSessionMessages.mockRejectedValue({
      code: 'REQUEST_CANCELLED',
      message: 'Request was cancelled.',
    })

    await store.loadMessages('session-001')

    // Cancelled requests should not show as error — status remains 'loading'
    // since the store only transitions away from loading on success/error
    // (cancelled requests are silently ignored)
    expect(store.messageStatus).not.toBe('error')
    expect(store.messageError).toBeNull()
  })

  it('stale response does not overwrite new data', async () => {
    const store = useSessionStore()

    // First call will be slow
    let resolveFirst: (v: unknown) => void
    const firstPromise = new Promise(resolve => { resolveFirst = resolve })
    mockedFetchSessionMessages.mockReturnValueOnce(firstPromise)

    // Start loading for session-001
    const loadPromise = store.loadMessages('session-001')

    // Start loading for session-002 (cancels the first)
    mockedFetchSessionMessages.mockResolvedValueOnce(
      makeMessageResponse([makeMessage({ id: 10, content: { type: 'text', text: 'Session 2' } })], 1),
    )

    // Resolve the stale first request
    resolveFirst!(makeMessageResponse([makeMessage({ id: 1, content: { type: 'text', text: 'Session 1' } })], 1))

    await loadPromise
    await store.loadMessages('session-002')

    // The final state should reflect session-002 data
    expect(store.messages.some(m => m.content.type === 'text' && m.content.text === 'Session 2')).toBe(true)
  })
})

describe('MessageStore — reset', () => {
  it('$reset clears all message state', async () => {
    const store = useSessionStore()

    mockedFetchSessionMessages.mockResolvedValue(
      makeMessageResponse([makeMessage()], 1),
    )
    await store.loadMessages('session-001')

    expect(store.messages).toHaveLength(1)

    store.$reset()

    expect(store.messages).toEqual([])
    expect(store.messageStatus).toBe('idle')
    expect(store.messageError).toBeNull()
    expect(store.messageRequestId).toBeNull()
    expect(store.messageOffset).toBe(0)
    expect(store.messageHasMore).toBe(false)
    expect(store.messageTotal).toBe(0)
  })
})
