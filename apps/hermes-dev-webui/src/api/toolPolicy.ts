/**
 * Tool Policy API functions for the Dev WebUI.
 *
 * Provides typed wrappers for the tool policy read-only endpoints:
 * - GET /api/dev/v1/tools/policy
 * - GET /api/dev/v1/tools/catalog
 *
 * Only GET requests. No POST/PUT/PATCH/DELETE tool methods exist.
 */

import { apiGet } from './client'
import type {
  ToolPolicyStatusResponse,
  ToolCatalogResponse,
  ToolCatalogFilters,
  ToolRiskLevel,
  ToolCapability,
  ToolPolicyStatus,
  ToolCatalogSort,
} from '@/types/api/toolPolicy'

/** API prefix matching the Dev Web API. */
const API_PREFIX = '/api/dev/v1'

/**
 * Build query string from catalog filter parameters.
 *
 * Only includes non-empty, non-default values.
 * All parameter names use camelCase matching the backend query contract.
 * Never sends dangerous parameters (execute, force, enable, write, dispatch, override).
 */
function buildCatalogQueryString(filters: ToolCatalogFilters): string {
  const searchParams = new URLSearchParams()

  const q = filters.q.trim()
  if (q !== '') {
    searchParams.set('q', q)
  }

  if (filters.risk !== undefined) {
    searchParams.set('risk', filters.risk)
  }

  if (filters.capability !== undefined) {
    searchParams.set('capability', filters.capability)
  }

  if (filters.policyStatus !== undefined) {
    searchParams.set('policyStatus', filters.policyStatus)
  }

  if (filters.page > 1) {
    searchParams.set('page', String(filters.page))
  }

  if (filters.pageSize !== 25) {
    searchParams.set('pageSize', String(filters.pageSize))
  }

  if (filters.sort !== 'nameAsc') {
    searchParams.set('sort', filters.sort)
  }

  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

/**
 * Fetch tool policy status.
 *
 * Returns the complete static policy: mode, counts, execution flags,
 * safety flags, and global limits. All execution flags are false.
 */
export async function fetchToolPolicyStatus(signal?: AbortSignal) {
  return apiGet<ToolPolicyStatusResponse>(
    `${API_PREFIX}/tools/policy`,
    undefined,
    signal,
  )
}

/**
 * Fetch the tool catalog with filtering, sorting, and pagination.
 *
 * Only accepts strictly typed ToolCatalogFilters — no arbitrary params.
 */
export async function fetchToolCatalog(
  filters: ToolCatalogFilters,
  signal?: AbortSignal,
) {
  const qs = buildCatalogQueryString(filters)
  return apiGet<ToolCatalogResponse>(
    `${API_PREFIX}/tools/catalog${qs}`,
    undefined,
    signal,
  )
}

// ── Re-export types for convenience ──

export type {
  ToolRiskLevel as ToolRiskLevelParam,
  ToolCapability as ToolCapabilityParam,
  ToolPolicyStatus as ToolPolicyStatusParam,
  ToolCatalogSort as ToolCatalogSortParam,
}
