/**
 * Context preview API function for the Dev WebUI.
 *
 * Provides a typed wrapper for the context preview endpoint:
 * - POST /api/dev/v1/context/preview
 */

import { apiPost } from './client'
import type { ContextPreviewData, ContextPreviewRequest } from '@/types/api/context'

/** API prefix matching the Dev Web API. */
const API_PREFIX = '/api/dev/v1'

/**
 * Preview memory context for a query.
 *
 * Pure read-only preview — no side effects, no LLM calls, no writes.
 */
export async function previewContext(
  request: ContextPreviewRequest,
  signal?: AbortSignal,
) {
  return apiPost<ContextPreviewData>(
    `${API_PREFIX}/context/preview`,
    request,
    undefined,
    signal,
  )
}
