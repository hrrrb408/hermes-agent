/**
 * Session API functions for the Dev WebUI.
 *
 * Provides typed wrappers for the session endpoints:
 * - GET /api/dev/v1/sessions
 * - GET /api/dev/v1/sessions/{sessionId}
 */

import { apiGet } from './client'
import type {
  SessionListData,
  SessionDetail,
  SessionListParams,
} from '@/types/api/session'

/** API prefix matching the Dev Web API. */
const API_PREFIX = '/api/dev/v1'

/**
 * Build query string from session list parameters.
 *
 * Only includes parameters with non-default values.
 */
function buildListQueryString(params: SessionListParams): string {
  const searchParams = new URLSearchParams()

  if (params.limit !== undefined && params.limit !== 30) {
    searchParams.set('limit', String(params.limit))
  }
  if (params.offset !== undefined && params.offset > 0) {
    searchParams.set('offset', String(params.offset))
  }
  if (params.query !== undefined && params.query.trim() !== '') {
    searchParams.set('query', params.query.trim())
  }
  if (params.source !== undefined) {
    searchParams.set('source', params.source)
  }
  if (params.order !== undefined && params.order !== 'recent') {
    searchParams.set('order', params.order)
  }
  if (params.archived !== undefined && params.archived !== 'exclude') {
    searchParams.set('archived', params.archived)
  }

  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

/**
 * Fetch the session list from the Dev API.
 *
 * @param params - Query parameters for filtering, pagination, and sorting.
 * @param signal - Optional AbortSignal for cancellation.
 * @returns Session list data with pagination metadata.
 */
export async function fetchSessions(
  params: SessionListParams = {},
  signal?: AbortSignal,
) {
  const qs = buildListQueryString(params)
  const response = await apiGet<SessionListData>(
    `${API_PREFIX}/sessions${qs}`,
    undefined,
    signal,
  )
  return response
}

/**
 * Fetch a single session's detail from the Dev API.
 *
 * @param sessionId - The session ID to fetch.
 * @param signal - Optional AbortSignal for cancellation.
 * @returns Session detail data.
 */
export async function fetchSessionDetail(
  sessionId: string,
  signal?: AbortSignal,
) {
  const encodedId = encodeURIComponent(sessionId)
  const response = await apiGet<SessionDetail>(
    `${API_PREFIX}/sessions/${encodedId}`,
    undefined,
    signal,
  )
  return response
}
