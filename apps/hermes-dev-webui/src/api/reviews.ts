/**
 * Review Queue API functions for the Dev WebUI.
 *
 * Provides typed wrappers for the review queue endpoints:
 * - GET /api/dev/v1/reviews/status
 * - GET /api/dev/v1/reviews
 * - GET /api/dev/v1/reviews/{reviewId}
 *
 * All endpoints are read-only. No write functions are provided.
 */

import { apiGet } from './client'
import type {
  ReviewQueueStatus,
  ReviewListData,
  ReviewDetail,
  ReviewListParams,
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
