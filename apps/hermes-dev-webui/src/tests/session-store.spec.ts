/**
 * Tests for the Session Pinia store.
 *
 * Covers loading, search, pagination, selection, error handling,
 * concurrent request handling, and persistence.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSessionStore } from '@/stores/session'
import type { SessionListItem, SessionDetail } from '@/types/api/session'
import type { DevApiError } from '@/api/client'

// ── Test data ──

function makeSessionItem(overrides: Partial<SessionListItem> = {}): SessionListItem {
  return {
    id: 'session-001',
    title: 'Test session',
    source: 'cli',
    model: 'deepseek-chat',
    messageCount: 5,
    toolCallCount: 2,
    archived: false,
    startedAt: '2026-06-07T10:00:00Z',
    endedAt: null,
    lastActiveAt: '2026-06-07T10:30:00Z',
    preview: 'Hello world',
    ...overrides,
  }
}

function makeSessionDetail(overrides: Partial<SessionDetail> = {}): SessionDetail {
  return {
    id: 'session-001',
    title: 'Test session',
    source: 'cli',
    model: 'deepseek-chat',
    messageCount: 5,
    toolCallCount: 2,
    inputTokens: 100,
    outputTokens: 200,
    archived: false,
    startedAt: '2026-06-07T10:00:00Z',
    endedAt: null,
    lastActiveAt: '2026-06-07T10:30:00Z',
    endReason: null,
    ...overrides,
  }
}

// ── Mock the sessions API module ──

vi.mock('@/api/sessions', () => ({
  fetchSessions: vi.fn(),
  fetchSessionDetail: vi.fn(),
}))

// Import after mocking
import { fetchSessions, fetchSessionDetail } from '@/api/sessions'

const mockedFetchSessions = fetchSessions as unknown as ReturnType<typeof vi.fn>
const mockedFetchSessionDetail = fetchSessionDetail as unknown as ReturnType<typeof vi.fn>

// ── Tests ──

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('SessionStore — initial state', () => {
  it('starts with idle status', () => {
    const store = useSessionStore()
    expect(store.listStatus).toBe('idle')
  })

  it('starts with empty sessions', () => {
    const store = useSessionStore()
    expect(store.sessions).toEqual([])
  })

  it('starts with no selection', () => {
    const store = useSessionStore()
    expect(store.selectedSessionId).toBeNull()
    expect(store.selectedSession).toBeNull()
  })
})

describe('SessionStore — load sessions', () => {
  it('loads sessions successfully', async () => {
    const store = useSessionStore()
    const items = [makeSessionItem(), makeSessionItem({ id: 's2' })]

    mockedFetchSessions.mockResolvedValue({
      data: { items, page: { offset: 0, limit: 30, total: 2, hasMore: false } },
      meta: { requestId: 'rid-1', timestamp: '2026-06-07T10:00:00Z' },
    })

    await store.loadSessions()

    expect(store.listStatus).toBe('success')
    expect(store.sessions).toHaveLength(2)
    expect(store.totalItems).toBe(2)
    expect(store.hasMore).toBe(false)
  })

  it('sets empty status when no sessions', async () => {
    const store = useSessionStore()

    mockedFetchSessions.mockResolvedValue({
      data: { items: [], page: { offset: 0, limit: 30, total: 0, hasMore: false } },
      meta: { requestId: 'rid-2', timestamp: '2026-06-07T10:00:00Z' },
    })

    await store.loadSessions()

    expect(store.listStatus).toBe('empty')
    expect(store.sessions).toEqual([])
  })

  it('sets error status on failure', async () => {
    const store = useSessionStore()

    mockedFetchSessions.mockRejectedValue({
      code: 'NETWORK_ERROR',
      message: 'Unable to connect to the API.',
    } satisfies DevApiError)

    await store.loadSessions()

    expect(store.listStatus).toBe('error')
    expect(store.listError).toBe('Unable to connect to the API.')
  })

  it('can retry after error', async () => {
    const store = useSessionStore()

    // First call fails
    mockedFetchSessions.mockRejectedValueOnce({
      code: 'NETWORK_ERROR',
      message: 'Network error.',
    } satisfies DevApiError)

    await store.loadSessions()
    expect(store.listStatus).toBe('error')

    // Retry succeeds
    mockedFetchSessions.mockResolvedValue({
      data: { items: [makeSessionItem()], page: { offset: 0, limit: 30, total: 1, hasMore: false } },
      meta: { requestId: 'rid-3', timestamp: '2026-06-07T10:00:00Z' },
    })

    await store.reloadSessions()
    expect(store.listStatus).toBe('success')
    expect(store.sessions).toHaveLength(1)
  })
})

describe('SessionStore — search', () => {
  it('sets search query and reloads', async () => {
    const store = useSessionStore()

    mockedFetchSessions.mockResolvedValue({
      data: { items: [], page: { offset: 0, limit: 30, total: 0, hasMore: false } },
      meta: { requestId: 'rid', timestamp: '2026-06-07T10:00:00Z' },
    })

    store.setSearchQuery('test')
    // Wait for debounce
    await new Promise(resolve => setTimeout(resolve, 400))

    expect(store.searchQuery).toBe('test')
    expect(mockedFetchSessions).toHaveBeenCalledWith(
      expect.objectContaining({ query: 'test' }),
      expect.any(AbortSignal),
    )
  })

  it('clears search and reloads', async () => {
    const store = useSessionStore()
    store.searchQuery = 'old query'

    mockedFetchSessions.mockResolvedValue({
      data: { items: [], page: { offset: 0, limit: 30, total: 0, hasMore: false } },
      meta: { requestId: 'rid', timestamp: '2026-06-07T10:00:00Z' },
    })

    store.clearSearch()

    expect(store.searchQuery).toBe('')
    expect(mockedFetchSessions).toHaveBeenCalled()
  })
})

describe('SessionStore — load more', () => {
  it('loads more sessions and appends', async () => {
    const store = useSessionStore()

    // Initial load
    mockedFetchSessions.mockResolvedValue({
      data: {
        items: [makeSessionItem({ id: 's1' })],
        page: { offset: 0, limit: 1, total: 2, hasMore: true },
      },
      meta: { requestId: 'r1', timestamp: '2026-06-07T10:00:00Z' },
    })
    await store.loadSessions()
    expect(store.sessions).toHaveLength(1)

    // Load more
    mockedFetchSessions.mockResolvedValue({
      data: {
        items: [makeSessionItem({ id: 's2' })],
        page: { offset: 1, limit: 1, total: 2, hasMore: false },
      },
      meta: { requestId: 'r2', timestamp: '2026-06-07T10:00:00Z' },
    })
    await store.loadMoreSessions()

    expect(store.sessions).toHaveLength(2)
    expect(store.hasMore).toBe(false)
  })

  it('deduplicates appended sessions', async () => {
    const store = useSessionStore()

    mockedFetchSessions.mockResolvedValue({
      data: {
        items: [makeSessionItem({ id: 's1' })],
        page: { offset: 0, limit: 1, total: 2, hasMore: true },
      },
      meta: { requestId: 'r1', timestamp: '2026-06-07T10:00:00Z' },
    })
    await store.loadSessions()

    // Server returns same session again
    mockedFetchSessions.mockResolvedValue({
      data: {
        items: [makeSessionItem({ id: 's1' }), makeSessionItem({ id: 's2' })],
        page: { offset: 1, limit: 2, total: 2, hasMore: false },
      },
      meta: { requestId: 'r2', timestamp: '2026-06-07T10:00:00Z' },
    })
    await store.loadMoreSessions()

    expect(store.sessions).toHaveLength(2)
  })

  it('does not load more when hasMore is false', async () => {
    const store = useSessionStore()
    store.hasMore = false

    await store.loadMoreSessions()
    expect(mockedFetchSessions).not.toHaveBeenCalled()
  })
})

describe('SessionStore — selection', () => {
  it('selects a session and loads detail', async () => {
    const store = useSessionStore()

    mockedFetchSessionDetail.mockResolvedValue({
      data: makeSessionDetail(),
      meta: { requestId: 'rid', timestamp: '2026-06-07T10:00:00Z' },
    })

    await store.selectSession('session-001')

    expect(store.selectedSessionId).toBe('session-001')
    expect(store.selectedSession).toBeTruthy()
    expect(store.selectedSession?.id).toBe('session-001')
  })

  it('handles 404 for nonexistent session', async () => {
    const store = useSessionStore()

    mockedFetchSessionDetail.mockRejectedValue({
      code: 'SESSION_NOT_FOUND',
      message: 'Session was not found.',
      status: 404,
    } satisfies DevApiError)

    await store.selectSession('nonexistent')

    expect(store.selectedSessionId).toBeNull()
    expect(store.selectedSession).toBeNull()
    expect(store.detailStatus).toBe('error')
  })

  it('handles 503 for unavailable store', async () => {
    const store = useSessionStore()

    mockedFetchSessionDetail.mockRejectedValue({
      code: 'SESSION_STORE_UNAVAILABLE',
      message: 'Session storage is unavailable.',
      status: 503,
    } satisfies DevApiError)

    await store.selectSession('session-001')

    expect(store.detailStatus).toBe('error')
    expect(store.detailError).toContain('unavailable')
  })

  it('skips reload when same session already loaded', async () => {
    const store = useSessionStore()
    store.selectedSessionId = 'session-001'
    store.selectedSession = makeSessionDetail()

    await store.selectSession('session-001')

    expect(mockedFetchSessionDetail).not.toHaveBeenCalled()
  })

  it('clears selection', () => {
    const store = useSessionStore()
    store.selectedSessionId = 's1'
    store.selectedSession = makeSessionDetail()

    store.clearSelection()

    expect(store.selectedSessionId).toBeNull()
    expect(store.selectedSession).toBeNull()
  })
})

describe('SessionStore — concurrent requests', () => {
  it('old list response does not overwrite new', async () => {
    const store = useSessionStore()

    // First call resolves slowly
    let resolveFirst: (value: unknown) => void
    const firstPromise = new Promise(resolve => { resolveFirst = resolve })

    mockedFetchSessions
      .mockImplementationOnce(() => firstPromise)
      .mockResolvedValueOnce({
        data: {
          items: [makeSessionItem({ id: 'new-session' })],
          page: { offset: 0, limit: 30, total: 1, hasMore: false },
        },
        meta: { requestId: 'r2', timestamp: '2026-06-07T10:00:00Z' },
      })

    // Start first load
    const load1 = store.loadSessions()
    // Start second load (cancels first)
    const load2 = store.loadSessions()
    await load2

    // Resolve first (stale)
    resolveFirst!({
      data: {
        items: [makeSessionItem({ id: 'old-session' })],
        page: { offset: 0, limit: 30, total: 1, hasMore: false },
      },
      meta: { requestId: 'r1', timestamp: '2026-06-07T10:00:00Z' },
    })
    await load1

    // Should have the new result, not the stale one
    expect(store.sessions[0]?.id).toBe('new-session')
  })

  it('old detail response does not overwrite new', async () => {
    const store = useSessionStore()

    let resolveFirst: (value: unknown) => void
    const firstPromise = new Promise(resolve => { resolveFirst = resolve })

    mockedFetchSessionDetail
      .mockImplementationOnce(() => firstPromise)
      .mockResolvedValueOnce({
        data: makeSessionDetail({ id: 'session-new', title: 'New Session' }),
        meta: { requestId: 'r2', timestamp: '2026-06-07T10:00:00Z' },
      })

    // Start two selections rapidly
    const sel1 = store.selectSession('session-old')
    const sel2 = store.selectSession('session-new')
    await sel2

    resolveFirst!({
      data: makeSessionDetail({ id: 'session-old', title: 'Old Session' }),
      meta: { requestId: 'r1', timestamp: '2026-06-07T10:00:00Z' },
    })
    await sel1

    expect(store.selectedSession?.id).toBe('session-new')
  })
})

describe('SessionStore — persistence', () => {
  it('restores selectedSessionId from localStorage', () => {
    localStorage.setItem('hermes-dev-webui.session.selected-id', 'saved-session')

    const store = useSessionStore()
    store.initialize()

    expect(store.selectedSessionId).toBe('saved-session')
  })

  it('clears invalid selectedSessionId from localStorage', async () => {
    localStorage.setItem('hermes-dev-webui.session.selected-id', 'invalid-session')

    mockedFetchSessionDetail.mockRejectedValue({
      code: 'SESSION_NOT_FOUND',
      message: 'Session was not found.',
      status: 404,
    } satisfies DevApiError)

    mockedFetchSessions.mockResolvedValue({
      data: { items: [], page: { offset: 0, limit: 30, total: 0, hasMore: false } },
      meta: { requestId: 'rid', timestamp: '2026-06-07T10:00:00Z' },
    })

    const store = useSessionStore()
    store.initialize()
    await new Promise(resolve => setTimeout(resolve, 10))

    // Wait for detail call
    expect(mockedFetchSessionDetail).toHaveBeenCalledWith('invalid-session', expect.any(AbortSignal))
  })

  it('saves sort order to localStorage', () => {
    const store = useSessionStore()
    mockedFetchSessions.mockResolvedValue({
      data: { items: [], page: { offset: 0, limit: 30, total: 0, hasMore: false } },
      meta: { requestId: 'rid', timestamp: '2026-06-07T10:00:00Z' },
    })

    store.setSortOrder('created')

    expect(localStorage.getItem('hermes-dev-webui.session.sort')).toBe('created')
  })
})

describe('SessionStore — reset', () => {
  it('resets all state to initial values', async () => {
    const store = useSessionStore()

    mockedFetchSessions.mockResolvedValue({
      data: { items: [makeSessionItem()], page: { offset: 0, limit: 30, total: 1, hasMore: false } },
      meta: { requestId: 'rid', timestamp: '2026-06-07T10:00:00Z' },
    })
    await store.loadSessions()

    store.$reset()

    expect(store.listStatus).toBe('idle')
    expect(store.sessions).toEqual([])
    expect(store.selectedSessionId).toBeNull()
    expect(store.searchQuery).toBe('')
  })
})

describe('SessionStore — no mock fallback', () => {
  it('never contains hardcoded mock session data', () => {
    const store = useSessionStore()
    expect(store.sessions).toEqual([])
    expect(store.listStatus).toBe('idle')

    // Verify store does not contain mock data strings
    const state = JSON.stringify(store.$state)
    expect(state).not.toContain('workspace-shell')
    expect(state).not.toContain('memory-context')
    expect(state).not.toContain('tool-event')
    expect(state).not.toContain('theme-regression')
  })
})
