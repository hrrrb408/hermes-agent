/**
 * Review Queue store for the Dev WebUI.
 *
 * Manages loading, error, and data state for the Review panel.
 * Phase 1A: read-only. No approve/reject/enqueue actions.
 * Phase 1B: dry-run preview only. No real approve/reject/enqueue.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import {
  fetchReviewStatus,
  fetchReviews,
  fetchReviewDetail,
  dryRunApproveReview,
  dryRunRejectReview,
} from '@/api/reviews'
import { isDevApiError } from '@/api/client'

import type {
  ReviewQueueStatus,
  ReviewListItem,
  ReviewDetail,
  ReviewListParams,
  ReviewStatusFilter,
  ReviewDecisionFilter,
  ReviewOrder,
  DryRunResult,
  DryRunAction,
} from '@/types/api/review'
import type { LoadingState } from '@/stores/workspacePanel'

export const useReviewStore = defineStore('workspace-review', () => {
  // ── State ──

  const statusState = ref<LoadingState>('idle')
  const listState = ref<LoadingState>('idle')
  const detailState = ref<LoadingState>('idle')

  const status = ref<ReviewQueueStatus | null>(null)
  const items = ref<readonly ReviewListItem[]>([])
  const page = ref({ total: 0, hasMore: false, offset: 0, limit: 30 })
  const detail = ref<ReviewDetail | null>(null)

  const statusError = ref('')
  const listError = ref('')
  const detailError = ref('')

  // Dry-run state
  const dryRunState = ref<LoadingState>('idle')
  const dryRunResult = ref<DryRunResult | null>(null)
  const dryRunError = ref('')
  const dryRunAction = ref<DryRunAction | null>(null)

  // Filters
  const statusFilter = ref<ReviewStatusFilter | undefined>(undefined)
  const decisionFilter = ref<ReviewDecisionFilter | undefined>(undefined)
  const categoryFilter = ref('')
  const queryFilter = ref('')
  const orderFilter = ref<ReviewOrder>('updated_desc')

  // Abort controllers
  let statusAbort: AbortController | null = null
  let listAbort: AbortController | null = null
  let detailAbort: AbortController | null = null
  let dryRunAbort: AbortController | null = null

  // ── Computed ──

  const isAvailable = computed(() => status.value?.available ?? false)
  const pendingCount = computed(() => status.value?.counts.pending ?? 0)
  const totalCount = computed(() => status.value?.counts.total ?? 0)

  const isDryRunLoading = computed(() => dryRunState.value === 'loading')
  const isDryRunAvailable = computed(() => status.value?.dryRunEnabled ?? false)

  // ── Helpers ──

  function handleError(err: unknown): string {
    if (isDevApiError(err)) {
      return err.message
    }
    return 'An unexpected error occurred.'
  }

  // ── Actions ──

  async function loadStatus(): Promise<void> {
    statusAbort?.abort()
    statusAbort = new AbortController()
    statusState.value = 'loading'
    statusError.value = ''

    try {
      const response = await fetchReviewStatus(statusAbort.signal)
      status.value = response.data
      statusState.value = response.data.available ? 'success' : 'empty'
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      statusError.value = handleError(err)
      statusState.value = 'error'
    }
  }

  async function loadReviews(params?: ReviewListParams): Promise<void> {
    listAbort?.abort()
    listAbort = new AbortController()
    listState.value = 'loading'
    listError.value = ''

    try {
      const response = await fetchReviews(
        {
          status: statusFilter.value,
          decision: decisionFilter.value,
          category: categoryFilter.value || undefined,
          query: queryFilter.value || undefined,
          order: orderFilter.value,
          ...params,
        },
        listAbort.signal,
      )
      items.value = response.data.items
      page.value = response.data.page
      listState.value = response.data.items.length > 0 ? 'success' : 'empty'
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      listError.value = handleError(err)
      listState.value = 'error'
    }
  }

  async function loadMoreReviews(): Promise<void> {
    if (!page.value.hasMore) return
    await loadReviews({ offset: page.value.offset + page.value.limit })
  }

  async function loadReviewDetail(reviewId: string): Promise<void> {
    detailAbort?.abort()
    detailAbort = new AbortController()
    detailState.value = 'loading'
    detailError.value = ''
    detail.value = null

    try {
      const response = await fetchReviewDetail(reviewId, detailAbort.signal)
      detail.value = response.data
      detailState.value = 'success'
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      detailError.value = handleError(err)
      detailState.value = 'error'
    }
  }

  function selectReview(reviewId: string): void {
    if (detail.value?.reviewId === reviewId) {
      clearSelection()
    } else {
      loadReviewDetail(reviewId)
    }
  }

  function clearSelection(): void {
    detailAbort?.abort()
    detail.value = null
    detailState.value = 'idle'
    detailError.value = ''
  }

  function setStatusFilter(value: ReviewStatusFilter | undefined): void {
    statusFilter.value = value
  }

  function setDecisionFilter(value: ReviewDecisionFilter | undefined): void {
    decisionFilter.value = value
  }

  function setCategoryFilter(value: string): void {
    categoryFilter.value = value
  }

  function setQueryFilter(value: string): void {
    queryFilter.value = value
  }

  function setOrderFilter(value: ReviewOrder): void {
    orderFilter.value = value
  }

  // ── Dry-run actions ──

  async function runApproveDryRun(reviewId: string): Promise<void> {
    dryRunAbort?.abort()
    dryRunAbort = new AbortController()
    dryRunState.value = 'loading'
    dryRunError.value = ''
    dryRunResult.value = null
    dryRunAction.value = 'APPROVE'

    try {
      const response = await dryRunApproveReview(
        reviewId,
        { includeDiff: true },
        dryRunAbort.signal,
      )
      dryRunResult.value = response.data
      dryRunState.value = 'success'
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      dryRunError.value = handleError(err)
      dryRunState.value = 'error'
    }
  }

  async function runRejectDryRun(reviewId: string, reason?: string): Promise<void> {
    dryRunAbort?.abort()
    dryRunAbort = new AbortController()
    dryRunState.value = 'loading'
    dryRunError.value = ''
    dryRunResult.value = null
    dryRunAction.value = 'REJECT'

    try {
      const response = await dryRunRejectReview(
        reviewId,
        { reason, includeDiff: true },
        dryRunAbort.signal,
      )
      dryRunResult.value = response.data
      dryRunState.value = 'success'
    } catch (err: unknown) {
      if (isDevApiError(err) && err.code === 'REQUEST_CANCELLED') return
      dryRunError.value = handleError(err)
      dryRunState.value = 'error'
    }
  }

  function clearDryRun(): void {
    dryRunAbort?.abort()
    dryRunResult.value = null
    dryRunError.value = ''
    dryRunState.value = 'idle'
    dryRunAction.value = null
  }

  async function refresh(): Promise<void> {
    await Promise.all([loadStatus(), loadReviews()])
  }

  return {
    // State
    statusState,
    listState,
    detailState,
    status,
    items,
    page,
    detail,
    statusError,
    listError,
    detailError,
    // Dry-run state
    dryRunState,
    dryRunResult,
    dryRunError,
    dryRunAction,
    // Filters
    statusFilter,
    decisionFilter,
    categoryFilter,
    queryFilter,
    orderFilter,
    // Computed
    isAvailable,
    pendingCount,
    totalCount,
    isDryRunLoading,
    isDryRunAvailable,
    // Actions
    loadStatus,
    loadReviews,
    loadMoreReviews,
    loadReviewDetail,
    selectReview,
    clearSelection,
    setStatusFilter,
    setDecisionFilter,
    setCategoryFilter,
    setQueryFilter,
    setOrderFilter,
    // Dry-run actions
    runApproveDryRun,
    runRejectDryRun,
    clearDryRun,
    refresh,
  }
})
