/**
 * Message API functions for the Dev WebUI.
 *
 * Provides typed wrappers for the message endpoint:
 * - GET /api/dev/v1/sessions/{sessionId}/messages
 */

import { apiGet } from './client'
import type { MessageListData, MessageListParams } from '@/types/api/message'

/** API prefix matching the Dev Web API. */
const API_PREFIX = '/api/dev/v1'

/**
 * Build query string from message list parameters.
 *
 * Only includes parameters with non-default values.
 */
function buildMessageQueryString(params: MessageListParams): string {
  const searchParams = new URLSearchParams()

  if (params.limit !== undefined && params.limit !== 50) {
    searchParams.set('limit', String(params.limit))
  }
  if (params.offset !== undefined && params.offset > 0) {
    searchParams.set('offset', String(params.offset))
  }
  if (params.before !== undefined) {
    searchParams.set('before', String(params.before))
  }
  if (params.after !== undefined) {
    searchParams.set('after', String(params.after))
  }

  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

/**
 * Fetch messages for a session from the Dev API.
 *
 * @param sessionId - The session ID to fetch messages for.
 * @param params - Query parameters for pagination and anchor filtering.
 * @param signal - Optional AbortSignal for cancellation.
 * @returns Message list data with pagination metadata.
 */
export async function fetchSessionMessages(
  sessionId: string,
  params: MessageListParams = {},
  signal?: AbortSignal,
) {
  const encodedId = encodeURIComponent(sessionId)
  const qs = buildMessageQueryString(params)
  const response = await apiGet<MessageListData>(
    `${API_PREFIX}/sessions/${encodedId}/messages${qs}`,
    undefined,
    signal,
  )
  return response
}
