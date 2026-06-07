/**
 * Session store for the Dev WebUI.
 *
 * Manages session list, detail, search, pagination, and selection state.
 * Loads data from the Dev Web API — never falls back to mock data.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchSessions, fetchSessionDetail } from '@/api/sessions'
import { fetchSessionMessages } from '@/api/messages'
import type {
  SessionListItem,
  SessionDetail,
  SessionSortOrder,
  SessionArchivedFilter,
} from '@/types/api/session'
import type { SessionMessage } from '@/types/api/message'
import { isDevApiError } from '@/api/client'

// ── Types ──

export type LoadingStatus = 'idle' | 'loading' | 'success' | 'empty' | 'error' | 'loadingMore'

export interface SessionStoreState {
  // List
  sessions: SessionListItem[]
  listStatus: LoadingStatus
  listError: string | null
  listRequestId: string | null
  // Search
  searchQuery: string
  // Pagination
  currentOffset: number
  pageSize: number
  totalItems: number
  hasMore: boolean
  // Detail
  selectedSessionId: string | null
  selectedSession: SessionDetail | null
  detailStatus: LoadingStatus
  detailError: string | null
  detailRequestId: string | null
  // Messages
  messages: SessionMessage[]
  messageStatus: LoadingStatus
  messageError: string | null
  messageRequestId: string | null
  messageOffset: number
  messageHasMore: boolean
  messageTotal: number
  // Sort & filter
  sortOrder: SessionSortOrder
  archivedFilter: SessionArchivedFilter
}

// ── localStorage keys ──

const STORAGE_KEY_SELECTED_ID = 'hermes-dev-webui.session.selected-id'
const STORAGE_KEY_SORT = 'hermes-dev-webui.session.sort'
const STORAGE_KEY_ARCHIVED = 'hermes-dev-webui.session.archived'

function readStorageString(key: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  try {
    const value = localStorage.getItem(key)
    return value ?? fallback
  } catch {
    return fallback
  }
}

function writeStorageString(key: string, value: string): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(key, value)
  } catch {
    // Storage persistence is optional.
  }
}

function readStorageNullable(key: string): string | null {
  if (typeof window === 'undefined') return null
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function clearStorageKey(key: string): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.removeItem(key)
  } catch {
    // OK
  }
}

// ── Request sequencing ──

let _listRequestId = 0
let _detailRequestId = 0
let _messageRequestId = 0

// ── Debounce helper ──

function debounce(fn: () => void, ms: number): () => void {
  let timer: ReturnType<typeof setTimeout> | undefined
  return () => {
    if (timer !== undefined) clearTimeout(timer)
    timer = setTimeout(fn, ms)
  }
}

// ── Store definition ──

export const useSessionStore = defineStore('session', () => {
  // ── State ──

  const sessions = ref<SessionListItem[]>([])
  const listStatus = ref<LoadingStatus>('idle')
  const listError = ref<string | null>(null)
  const listRequestId = ref<string | null>(null)

  const searchQuery = ref('')

  const currentOffset = ref(0)
  const pageSize = ref(30)
  const totalItems = ref(0)
  const hasMore = ref(false)

  const selectedSessionId = ref<string | null>(null)
  const selectedSession = ref<SessionDetail | null>(null)
  const detailStatus = ref<LoadingStatus>('idle')
  const detailError = ref<string | null>(null)
  const detailRequestId = ref<string | null>(null)

  const sortOrder = ref<SessionSortOrder>('recent')
  const archivedFilter = ref<SessionArchivedFilter>('exclude')

  // Message state
  const messages = ref<SessionMessage[]>([])
  const messageStatus = ref<LoadingStatus>('idle')
  const messageError = ref<string | null>(null)
  const messageRequestId = ref<string | null>(null)
  const messageOffset = ref(0)
  const messageHasMore = ref(false)
  const messageTotal = ref(0)

  // Active abort controllers
  let _listAbortController: AbortController | null = null
  let _detailAbortController: AbortController | null = null
  let _messageAbortController: AbortController | null = null

  // ── Computed ──

  const isLoading = computed(() => listStatus.value === 'loading')
  const isLoadingMore = computed(() => listStatus.value === 'loadingMore')
  const isEmpty = computed(() => listStatus.value === 'empty')
  const hasError = computed(() => listStatus.value === 'error')
  const isDetailLoading = computed(() => detailStatus.value === 'loading')
  const hasDetailError = computed(() => detailStatus.value === 'error')
  const isMessageLoading = computed(() => messageStatus.value === 'loading')
  const isMessageLoadingMore = computed(() => messageStatus.value === 'loadingMore')
  const hasMessageError = computed(() => messageStatus.value === 'error')
  const isMessageEmpty = computed(() => messageStatus.value === 'empty')

  // ── Actions ──

  function cancelPendingList(): void {
    if (_listAbortController) {
      _listAbortController.abort()
      _listAbortController = null
    }
  }

  function cancelPendingDetail(): void {
    if (_detailAbortController) {
      _detailAbortController.abort()
      _detailAbortController = null
    }
  }

  function cancelPendingMessages(): void {
    if (_messageAbortController) {
      _messageAbortController.abort()
      _messageAbortController = null
    }
  }

  /**
   * Load sessions from the API. Replaces current list.
   */
  async function loadSessions(): Promise<void> {
    cancelPendingList()

    const thisRequestId = ++_listRequestId
    const controller = new AbortController()
    _listAbortController = controller

    listStatus.value = 'loading'
    listError.value = null
    currentOffset.value = 0

    try {
      const response = await fetchSessions(
        {
          limit: pageSize.value,
          offset: 0,
          query: searchQuery.value || undefined,
          order: sortOrder.value,
          archived: archivedFilter.value,
        },
        controller.signal,
      )

      // Discard stale response
      if (thisRequestId !== _listRequestId) return

      sessions.value = [...response.data.items]
      totalItems.value = response.data.page.total
      hasMore.value = response.data.page.hasMore
      currentOffset.value = response.data.page.offset
      listRequestId.value = response.meta.requestId
      listStatus.value = response.data.items.length === 0 ? 'empty' : 'success'
    } catch (err: unknown) {
      if (thisRequestId !== _listRequestId) return

      // Cancelled requests are not user-visible errors
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return

      listStatus.value = 'error'
      listError.value = isDevApiError(err) ? err.message : 'Unable to load sessions.'
      listRequestId.value = isDevApiError(err) ? err.requestId ?? null : null
    } finally {
      if (_listAbortController === controller) {
        _listAbortController = null
      }
    }
  }

  /**
   * Reload sessions (same as loadSessions — resets to page 1).
   */
  async function reloadSessions(): Promise<void> {
    return loadSessions()
  }

  /**
   * Load the next page of sessions and append.
   */
  async function loadMoreSessions(): Promise<void> {
    if (!hasMore.value || listStatus.value === 'loadingMore') return

    cancelPendingList()

    const thisRequestId = ++_listRequestId
    const controller = new AbortController()
    _listAbortController = controller

    listStatus.value = 'loadingMore'

    const nextOffset = currentOffset.value + pageSize.value

    try {
      const response = await fetchSessions(
        {
          limit: pageSize.value,
          offset: nextOffset,
          query: searchQuery.value || undefined,
          order: sortOrder.value,
          archived: archivedFilter.value,
        },
        controller.signal,
      )

      // Discard stale response
      if (thisRequestId !== _listRequestId) return

      // Append and deduplicate by ID
      const existing = new Set(sessions.value.map(s => s.id))
      const newItems = response.data.items.filter(s => !existing.has(s.id))
      sessions.value = [...sessions.value, ...newItems]
      totalItems.value = response.data.page.total
      hasMore.value = response.data.page.hasMore
      currentOffset.value = nextOffset
      listRequestId.value = response.meta.requestId
      listStatus.value = 'success'
    } catch (err: unknown) {
      if (thisRequestId !== _listRequestId) return
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return

      listStatus.value = 'error'
      listError.value = isDevApiError(err) ? err.message : 'Unable to load more sessions.'
    } finally {
      if (_listAbortController === controller) {
        _listAbortController = null
      }
    }
  }

  /**
   * Set search query and reload (debounced).
   */
  const debouncedSearch = debounce(() => loadSessions(), 300)

  function setSearchQuery(query: string): void {
    searchQuery.value = query
    debouncedSearch()
  }

  /**
   * Clear search and reload.
   */
  function clearSearch(): void {
    searchQuery.value = ''
    loadSessions()
  }

  /**
   * Set sort order and reload.
   */
  function setSortOrder(order: SessionSortOrder): void {
    sortOrder.value = order
    writeStorageString(STORAGE_KEY_SORT, order)
    loadSessions()
  }

  /**
   * Set archived filter and reload.
   */
  function setArchivedFilter(filter: SessionArchivedFilter): void {
    archivedFilter.value = filter
    writeStorageString(STORAGE_KEY_ARCHIVED, filter)
    loadSessions()
  }

  /**
   * Select a session and load its detail.
   */
  async function selectSession(sessionId: string): Promise<void> {
    // Skip if already selected and loaded
    if (selectedSessionId.value === sessionId && selectedSession.value) return

    selectedSessionId.value = sessionId
    selectedSession.value = null
    detailError.value = null
    // Reset message state for new session
    messages.value = []
    messageStatus.value = 'idle'
    messageError.value = null
    messageOffset.value = 0
    messageHasMore.value = false
    messageTotal.value = 0
    writeStorageString(STORAGE_KEY_SELECTED_ID, sessionId)

    await loadSessionDetail(sessionId)
    // Load messages after detail is loaded
    loadMessages(sessionId)
  }

  /**
   * Load detail for a specific session.
   */
  async function loadSessionDetail(sessionId: string): Promise<void> {
    cancelPendingDetail()

    const thisRequestId = ++_detailRequestId
    const controller = new AbortController()
    _detailAbortController = controller

    detailStatus.value = 'loading'
    detailError.value = null

    try {
      const response = await fetchSessionDetail(sessionId, controller.signal)

      // Discard stale response
      if (thisRequestId !== _detailRequestId) return

      selectedSession.value = response.data
      detailRequestId.value = response.meta.requestId
      detailStatus.value = 'success'
    } catch (err: unknown) {
      if (thisRequestId !== _detailRequestId) return
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return

      if (isDevApiError(err) && err.status === 404) {
        // Session not found — clear invalid selection
        selectedSessionId.value = null
        selectedSession.value = null
        clearStorageKey(STORAGE_KEY_SELECTED_ID)
        detailStatus.value = 'error'
        detailError.value = 'Session was not found.'
        return
      }

      detailStatus.value = 'error'
      detailError.value = isDevApiError(err) ? err.message : 'Unable to load session detail.'
      detailRequestId.value = isDevApiError(err) ? err.requestId ?? null : null
    } finally {
      if (_detailAbortController === controller) {
        _detailAbortController = null
      }
    }
  }

  /**
   * Load messages for the currently selected session.
   */
  async function loadMessages(sessionId?: string): Promise<void> {
    const targetId = sessionId ?? selectedSessionId.value
    if (!targetId) return

    cancelPendingMessages()

    const thisRequestId = ++_messageRequestId
    const controller = new AbortController()
    _messageAbortController = controller

    messageStatus.value = 'loading'
    messageError.value = null
    messageOffset.value = 0

    try {
      const response = await fetchSessionMessages(
        targetId,
        { limit: 50, offset: 0 },
        controller.signal,
      )

      // Discard stale response
      if (thisRequestId !== _messageRequestId) return

      messages.value = [...response.data.items]
      messageTotal.value = response.data.page.total
      messageHasMore.value = response.data.page.hasMore
      messageOffset.value = response.data.page.offset
      messageRequestId.value = response.meta.requestId
      messageStatus.value = response.data.items.length === 0 ? 'empty' : 'success'
    } catch (err: unknown) {
      if (thisRequestId !== _messageRequestId) return
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return

      messageStatus.value = 'error'
      messageError.value = isDevApiError(err) ? err.message : 'Unable to load messages.'
      messageRequestId.value = isDevApiError(err) ? err.requestId ?? null : null
    } finally {
      if (_messageAbortController === controller) {
        _messageAbortController = null
      }
    }
  }

  /**
   * Load more messages (next page) for the current session.
   */
  async function loadMoreMessages(): Promise<void> {
    if (!messageHasMore.value || messageStatus.value === 'loadingMore') return
    if (!selectedSessionId.value) return

    cancelPendingMessages()

    const thisRequestId = ++_messageRequestId
    const controller = new AbortController()
    _messageAbortController = controller

    messageStatus.value = 'loadingMore'

    const nextOffset = messageOffset.value + 50

    try {
      const response = await fetchSessionMessages(
        selectedSessionId.value,
        { limit: 50, offset: nextOffset },
        controller.signal,
      )

      if (thisRequestId !== _messageRequestId) return

      // Append and deduplicate by ID
      const existing = new Set(messages.value.map(m => m.id))
      const newItems = response.data.items.filter(m => !existing.has(m.id))
      messages.value = [...messages.value, ...newItems]
      messageTotal.value = response.data.page.total
      messageHasMore.value = response.data.page.hasMore
      messageOffset.value = nextOffset
      messageRequestId.value = response.meta.requestId
      messageStatus.value = 'success'
    } catch (err: unknown) {
      if (thisRequestId !== _messageRequestId) return
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return

      messageStatus.value = 'error'
      messageError.value = isDevApiError(err) ? err.message : 'Unable to load more messages.'
    } finally {
      if (_messageAbortController === controller) {
        _messageAbortController = null
      }
    }
  }

  /**
   * Clear the current session selection.
   */
  function clearSelection(): void {
    cancelPendingDetail()
    cancelPendingMessages()
    selectedSessionId.value = null
    selectedSession.value = null
    detailStatus.value = 'idle'
    detailError.value = null
    // Clear message state
    messages.value = []
    messageStatus.value = 'idle'
    messageError.value = null
    messageRequestId.value = null
    messageOffset.value = 0
    messageHasMore.value = false
    messageTotal.value = 0
    clearStorageKey(STORAGE_KEY_SELECTED_ID)
  }

  /**
   * Initialize the store: restore persisted state and load sessions.
   */
  function initialize(): void {
    // Restore sort and filter from localStorage
    const savedSort = readStorageString(STORAGE_KEY_SORT, 'recent')
    if (savedSort === 'recent' || savedSort === 'created') {
      sortOrder.value = savedSort
    }

    const savedArchived = readStorageString(STORAGE_KEY_ARCHIVED, 'exclude')
    if (['exclude', 'include', 'only'].includes(savedArchived)) {
      archivedFilter.value = savedArchived as SessionArchivedFilter
    }

    // Restore selected session ID (detail loaded later)
    const savedId = readStorageNullable(STORAGE_KEY_SELECTED_ID)
    if (savedId) {
      selectedSessionId.value = savedId
    }

    // Load session list
    loadSessions()

    // If we have a saved session ID, load its detail
    if (savedId) {
      loadSessionDetail(savedId)
      loadMessages(savedId)
    }
  }

  /**
   * Reset the store to initial state.
   */
  function $reset(): void {
    cancelPendingList()
    cancelPendingDetail()
    cancelPendingMessages()
    _listRequestId = 0
    _detailRequestId = 0
    _messageRequestId = 0
    sessions.value = []
    listStatus.value = 'idle'
    listError.value = null
    listRequestId.value = null
    searchQuery.value = ''
    currentOffset.value = 0
    pageSize.value = 30
    totalItems.value = 0
    hasMore.value = false
    selectedSessionId.value = null
    selectedSession.value = null
    detailStatus.value = 'idle'
    detailError.value = null
    detailRequestId.value = null
    // Message state
    messages.value = []
    messageStatus.value = 'idle'
    messageError.value = null
    messageRequestId.value = null
    messageOffset.value = 0
    messageHasMore.value = false
    messageTotal.value = 0
    sortOrder.value = 'recent'
    archivedFilter.value = 'exclude'
  }

  return {
    // State
    sessions,
    listStatus,
    listError,
    listRequestId,
    searchQuery,
    currentOffset,
    pageSize,
    totalItems,
    hasMore,
    selectedSessionId,
    selectedSession,
    detailStatus,
    detailError,
    detailRequestId,
    // Messages
    messages,
    messageStatus,
    messageError,
    messageRequestId,
    messageOffset,
    messageHasMore,
    messageTotal,
    sortOrder,
    archivedFilter,

    // Computed
    isLoading,
    isLoadingMore,
    isEmpty,
    hasError,
    isDetailLoading,
    hasDetailError,
    // Message computed
    isMessageLoading,
    isMessageLoadingMore,
    hasMessageError,
    isMessageEmpty,

    // Actions
    loadSessions,
    reloadSessions,
    loadMoreSessions,
    setSearchQuery,
    clearSearch,
    setSortOrder,
    setArchivedFilter,
    selectSession,
    loadSessionDetail,
    clearSelection,
    // Message actions
    loadMessages,
    loadMoreMessages,
    initialize,
    $reset,
  }
})
