/**
 * Memory API functions for the Dev WebUI.
 *
 * Provides typed wrappers for the memory endpoints:
 * - GET /api/dev/v1/memory/status
 * - GET /api/dev/v1/memory/categories
 * - GET /api/dev/v1/memory/items
 * - GET /api/dev/v1/memory/items/{memoryId}
 */

import { apiGet } from './client'
import type {
  MemoryStatusData,
  MemoryCategoryListData,
  MemoryItemListData,
  MemoryItemDetail,
  MemoryItemListParams,
} from '@/types/api/memory'

/** API prefix matching the Dev Web API. */
const API_PREFIX = '/api/dev/v1'

/**
 * Build query string from memory item list parameters.
 */
function buildItemListQueryString(params: MemoryItemListParams): string {
  const searchParams = new URLSearchParams()

  if (params.category !== undefined && params.category.trim() !== '') {
    searchParams.set('category', params.category.trim())
  }
  if (params.query !== undefined && params.query.trim() !== '') {
    searchParams.set('query', params.query.trim())
  }
  if (params.includeArchived === true) {
    searchParams.set('includeArchived', 'true')
  }
  if (params.limit !== undefined && params.limit !== 50) {
    searchParams.set('limit', String(params.limit))
  }
  if (params.offset !== undefined && params.offset > 0) {
    searchParams.set('offset', String(params.offset))
  }

  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

/**
 * Fetch memory system status.
 */
export async function fetchMemoryStatus(signal?: AbortSignal) {
  return apiGet<MemoryStatusData>(`${API_PREFIX}/memory/status`, undefined, signal)
}

/**
 * Fetch memory categories.
 */
export async function fetchMemoryCategories(
  includeArchived = false,
  signal?: AbortSignal,
) {
  const qs = includeArchived ? '?includeArchived=true' : ''
  return apiGet<MemoryCategoryListData>(
    `${API_PREFIX}/memory/categories${qs}`,
    undefined,
    signal,
  )
}

/**
 * Fetch memory items with optional filtering.
 */
export async function fetchMemoryItems(
  params: MemoryItemListParams = {},
  signal?: AbortSignal,
) {
  const qs = buildItemListQueryString(params)
  return apiGet<MemoryItemListData>(
    `${API_PREFIX}/memory/items${qs}`,
    undefined,
    signal,
  )
}

/**
 * Fetch a single memory item detail.
 */
export async function fetchMemoryItemDetail(
  memoryId: string,
  signal?: AbortSignal,
) {
  const encodedId = encodeURIComponent(memoryId)
  return apiGet<MemoryItemDetail>(
    `${API_PREFIX}/memory/items/${encodedId}`,
    undefined,
    signal,
  )
}
