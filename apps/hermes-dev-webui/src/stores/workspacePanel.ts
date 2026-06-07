/**
 * Workspace panel stores for Memory, Context, and Agent tabs.
 *
 * Each store manages loading, error, and data state for its panel.
 * All data is fetched from the read-only Dev API — no writes, no mocks.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import {
  fetchMemoryStatus,
  fetchMemoryCategories,
  fetchMemoryItems,
  fetchMemoryItemDetail,
} from '@/api/memory'
import { previewContext } from '@/api/context'
import { fetchAgentStatus } from '@/api/agent'
import { isDevApiError } from '@/api/client'

import type {
  MemoryStatusData,
  MemoryCategory,
  MemoryItem,
  MemoryItemDetail,
  MemoryItemListParams,
} from '@/types/api/memory'
import type { ContextPreviewData, ContextPreviewRequest } from '@/types/api/context'
import type { AgentStatusData } from '@/types/api/agent'

// ── Loading state type ──

export type LoadingState = 'idle' | 'loading' | 'success' | 'empty' | 'error'

// ── Memory Store ──

export const useMemoryStore = defineStore('workspace-memory', () => {
  const statusState = ref<LoadingState>('idle')
  const categoriesState = ref<LoadingState>('idle')
  const itemsState = ref<LoadingState>('idle')
  const detailState = ref<LoadingState>('idle')

  const status = ref<MemoryStatusData | null>(null)
  const categories = ref<readonly MemoryCategory[]>([])
  const items = ref<readonly MemoryItem[]>([])
  const itemsPage = ref({ total: 0, hasMore: false })
  const detail = ref<MemoryItemDetail | null>(null)

  const statusError = ref('')
  const categoriesError = ref('')
  const itemsError = ref('')
  const detailError = ref('')

  const includeArchived = ref(false)
  const categoryFilter = ref('')
  const queryFilter = ref('')

  let statusAbort: AbortController | null = null
  let categoriesAbort: AbortController | null = null
  let itemsAbort: AbortController | null = null
  let detailAbort: AbortController | null = null

  const isAvailable = computed(() => status.value?.available ?? false)
  const activeCategories = computed(() =>
    categories.value.filter(c => c.status === 'active'),
  )

  function _handleError(err: unknown): string {
    if (isDevApiError(err)) {
      return err.message
    }
    return 'An unexpected error occurred.'
  }

  async function loadStatus(): Promise<void> {
    statusAbort?.abort()
    statusAbort = new AbortController()
    statusState.value = 'loading'
    statusError.value = ''

    try {
      const response = await fetchMemoryStatus(statusAbort.signal)
      status.value = response.data
      statusState.value = response.data.available ? 'success' : 'empty'
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      statusError.value = _handleError(err)
      statusState.value = 'error'
    }
  }

  async function loadCategories(): Promise<void> {
    categoriesAbort?.abort()
    categoriesAbort = new AbortController()
    categoriesState.value = 'loading'
    categoriesError.value = ''

    try {
      const response = await fetchMemoryCategories(
        includeArchived.value,
        categoriesAbort.signal,
      )
      categories.value = response.data.items
      categoriesState.value = response.data.items.length > 0 ? 'success' : 'empty'
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      categoriesError.value = _handleError(err)
      categoriesState.value = 'error'
    }
  }

  async function loadItems(params?: MemoryItemListParams): Promise<void> {
    itemsAbort?.abort()
    itemsAbort = new AbortController()
    itemsState.value = 'loading'
    itemsError.value = ''

    try {
      const response = await fetchMemoryItems(
        {
          category: categoryFilter.value || undefined,
          query: queryFilter.value || undefined,
          includeArchived: includeArchived.value,
          ...params,
        },
        itemsAbort.signal,
      )
      items.value = response.data.items
      itemsPage.value = response.data.page
      itemsState.value = response.data.items.length > 0 ? 'success' : 'empty'
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      itemsError.value = _handleError(err)
      itemsState.value = 'error'
    }
  }

  async function loadDetail(memoryId: string): Promise<void> {
    detailAbort?.abort()
    detailAbort = new AbortController()
    detailState.value = 'loading'
    detailError.value = ''
    detail.value = null

    try {
      const response = await fetchMemoryItemDetail(memoryId, detailAbort.signal)
      detail.value = response.data
      detailState.value = 'success'
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      detailError.value = _handleError(err)
      detailState.value = 'error'
    }
  }

  function clearDetail(): void {
    detail.value = null
    detailState.value = 'idle'
    detailError.value = ''
  }

  function setIncludeArchived(value: boolean): void {
    includeArchived.value = value
  }

  function setCategoryFilter(value: string): void {
    categoryFilter.value = value
  }

  function setQueryFilter(value: string): void {
    queryFilter.value = value
  }

  return {
    statusState,
    categoriesState,
    itemsState,
    detailState,
    status,
    categories,
    items,
    itemsPage,
    detail,
    statusError,
    categoriesError,
    itemsError,
    detailError,
    includeArchived,
    categoryFilter,
    queryFilter,
    isAvailable,
    activeCategories,
    loadStatus,
    loadCategories,
    loadItems,
    loadDetail,
    clearDetail,
    setIncludeArchived,
    setCategoryFilter,
    setQueryFilter,
  }
})

// ── Context Store ──

export const useContextStore = defineStore('workspace-context', () => {
  const state = ref<LoadingState>('idle')
  const error = ref('')
  const preview = ref<ContextPreviewData | null>(null)
  const query = ref('')

  let abortController: AbortController | null = null

  function _handleError(err: unknown): string {
    if (isDevApiError(err)) {
      return err.message
    }
    return 'An unexpected error occurred.'
  }

  async function runPreview(requestQuery?: string): Promise<void> {
    abortController?.abort()
    abortController = new AbortController()
    state.value = 'loading'
    error.value = ''

    const effectiveQuery = requestQuery ?? query.value
    if (!effectiveQuery.trim()) {
      state.value = 'idle'
      return
    }

    const request: ContextPreviewRequest = {
      query: effectiveQuery.trim(),
      options: {
        showScores: true,
      },
    }

    try {
      const response = await previewContext(request, abortController.signal)
      preview.value = response.data
      state.value = response.data.memories.length > 0 ? 'success' : 'empty'
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      error.value = _handleError(err)
      state.value = 'error'
    }
  }

  function setQuery(value: string): void {
    query.value = value
  }

  function clearPreview(): void {
    preview.value = null
    state.value = 'idle'
    error.value = ''
  }

  return {
    state,
    error,
    preview,
    query,
    runPreview,
    setQuery,
    clearPreview,
  }
})

// ── Agent Store ──

export const useAgentStore = defineStore('workspace-agent', () => {
  const state = ref<LoadingState>('idle')
  const error = ref('')
  const status = ref<AgentStatusData | null>(null)

  let abortController: AbortController | null = null

  function _handleError(err: unknown): string {
    if (isDevApiError(err)) {
      return err.message
    }
    return 'An unexpected error occurred.'
  }

  async function loadStatus(): Promise<void> {
    abortController?.abort()
    abortController = new AbortController()
    state.value = 'loading'
    error.value = ''

    try {
      const response = await fetchAgentStatus(abortController.signal)
      status.value = response.data
      state.value = response.data.available ? 'success' : 'empty'
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      error.value = _handleError(err)
      state.value = 'error'
    }
  }

  return {
    state,
    error,
    status,
    loadStatus,
  }
})
