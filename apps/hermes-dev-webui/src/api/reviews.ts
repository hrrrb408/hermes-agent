/**
 * Review Queue API functions for the Dev WebUI.
 *
 * Provides typed wrappers for the review queue endpoints:
 * - GET /api/dev/v1/reviews/status
 * - GET /api/dev/v1/reviews
 * - GET /api/dev/v1/reviews/{reviewId}
 * - POST /api/dev/v1/reviews/{reviewId}/approve/dry-run
 * - POST /api/dev/v1/reviews/{reviewId}/reject/dry-run
 * - POST /api/dev/v1/reviews/{reviewId}/approve/execute
 * - POST /api/dev/v1/reviews/{reviewId}/reject/execute
 *
 * Phase 1A: read-only GET endpoints.
 * Phase 1B: dry-run POST endpoints (no side effects).
 * Phase 1C: dev-only execute POST endpoints (real side effects, gated by kill switch).
 * No bare approve/reject/enqueue functions are provided.
 */

import { apiGet, apiPost } from './client'
import type {
  ReviewQueueStatus,
  ReviewListData,
  ReviewDetail,
  ReviewListParams,
  DryRunResult,
  ApproveDryRunRequest,
  RejectDryRunRequest,
  ApproveExecuteRequest,
  RejectExecuteRequest,
  ReviewExecuteResult,
} from '@/types/api/review'

/** API prefix matching the Dev Web API. */
const API_PREFIX = '/api/dev/v1'

/**
 * Build query string from review list parameters.
 */
function buildReviewListQueryString(params: ReviewListParams): string {
  const searchParams = new URLSearchParams()

  if (params.status !== undefined) {
    searchParams.set('status', params.status)
  }
  if (params.decision !== undefined) {
    searchParams.set('decision', params.decision)
  }
  if (params.category !== undefined && params.category.trim() !== '') {
    searchParams.set('category', params.category.trim())
  }
  if (params.query !== undefined && params.query.trim() !== '') {
    searchParams.set('query', params.query.trim())
  }
  if (params.limit !== undefined && params.limit !== 30) {
    searchParams.set('limit', String(params.limit))
  }
  if (params.offset !== undefined && params.offset > 0) {
    searchParams.set('offset', String(params.offset))
  }
  if (params.order !== undefined && params.order !== 'updated_desc') {
    searchParams.set('order', params.order)
  }

  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

/**
 * Fetch review queue status.
 */
export async function fetchReviewStatus(signal?: AbortSignal) {
  return apiGet<ReviewQueueStatus>(`${API_PREFIX}/reviews/status`, undefined, signal)
}

/**
 * Fetch review items with optional filtering.
 */
export async function fetchReviews(
  params: ReviewListParams = {},
  signal?: AbortSignal,
) {
  const qs = buildReviewListQueryString(params)
  return apiGet<ReviewListData>(`${API_PREFIX}/reviews${qs}`, undefined, signal)
}

/**
 * Fetch a single review item detail.
 */
export async function fetchReviewDetail(
  reviewId: string,
  signal?: AbortSignal,
) {
  const encodedId = encodeURIComponent(reviewId)
  return apiGet<ReviewDetail>(
    `${API_PREFIX}/reviews/${encodedId}`,
    undefined,
    signal,
  )
}

/**
 * Preview what would happen if a review item were approved.
 *
 * This is a dry-run operation — no files are modified, no events
 * are appended, no memory is written, and no review status changes.
 */
export async function dryRunApproveReview(
  reviewId: string,
  payload: ApproveDryRunRequest = {},
  signal?: AbortSignal,
) {
  const encodedId = encodeURIComponent(reviewId)
  return apiPost<DryRunResult>(
    `${API_PREFIX}/reviews/${encodedId}/approve/dry-run`,
    payload,
    undefined,
    signal,
  )
}

/**
 * Preview what would happen if a review item were rejected.
 *
 * This is a dry-run operation — no files are modified, no events
 * are appended, and no review status changes.
 */
export async function dryRunRejectReview(
  reviewId: string,
  payload: RejectDryRunRequest = {},
  signal?: AbortSignal,
) {
  const encodedId = encodeURIComponent(reviewId)
  return apiPost<DryRunResult>(
    `${API_PREFIX}/reviews/${encodedId}/reject/dry-run`,
    payload,
    undefined,
    signal,
  )
}

/**
 * Execute a real approve on a review item (dev-only).
 *
 * This endpoint has real side effects: writes memory files,
 * updates review status, and appends audit events. Gated by
 * a fail-closed kill switch and dev-only environment guard.
 *
 * Requires explicit confirmation, dry-run preview, and
 * acknowledged effects.
 */
export async function executeApproveReview(
  reviewId: string,
  payload: ApproveExecuteRequest,
  signal?: AbortSignal,
) {
  const encodedId = encodeURIComponent(reviewId)
  return apiPost<ReviewExecuteResult>(
    `${API_PREFIX}/reviews/${encodedId}/approve/execute`,
    payload,
    undefined,
    signal,
  )
}

/**
 * Execute a real reject on a review item (dev-only).
 *
 * This endpoint has real side effects: updates review status
 * and appends audit events. No memory is written. Gated by
 * a fail-closed kill switch and dev-only environment guard.
 *
 * Requires explicit confirmation, dry-run preview, and
 * acknowledged effects.
 */
export async function executeRejectReview(
  reviewId: string,
  payload: RejectExecuteRequest,
  signal?: AbortSignal,
) {
  const encodedId = encodeURIComponent(reviewId)
  return apiPost<ReviewExecuteResult>(
    `${API_PREFIX}/reviews/${encodedId}/reject/execute`,
    payload,
    undefined,
    signal,
  )
}
