/**
 * TypeScript types for the Dev API memory endpoints.
 *
 * Matches the Phase 0C-05 API contract.
 */

// ── Memory Status ──

/** Memory system status response data. */
export interface MemoryStatusData {
  readonly available: boolean
  readonly readOnly: boolean
  readonly rootCategories: {
    readonly total: number
    readonly active: number
    readonly archived: number
  }
  readonly memories: {
    readonly total: number
    readonly active: number
    readonly archived: number
  }
  readonly capabilities: {
    readonly contextLoader: boolean
    readonly runtimeInjection: boolean
    readonly writer: boolean
    readonly reviewQueue: boolean
  }
  readonly exposedCapabilities: {
    readonly read: boolean
    readonly write: boolean
    readonly review: boolean
  }
}

// ── Memory Categories ──

/** A single memory category. */
export interface MemoryCategory {
  readonly key: string
  readonly title: string
  readonly description: string
  readonly priority: string
  readonly keywords: string
  readonly status: string
  readonly memoryCount: number
  readonly activeMemoryCount: number
}

/** Response data for GET /memory/categories. */
export interface MemoryCategoryListData {
  readonly items: readonly MemoryCategory[]
  readonly total: number
}

// ── Memory Items ──

/** A single memory item in list responses. */
export interface MemoryItem {
  readonly id: string
  readonly category: string
  readonly title: string
  readonly summary: string
  readonly tags: string
  readonly type: string
  readonly importance: string
  readonly status: string
  readonly updatedAt: string
}

/** Pagination metadata for memory items. */
export interface MemoryPage {
  readonly offset: number
  readonly limit: number
  readonly total: number
  readonly hasMore: boolean
}

/** Response data for GET /memory/items. */
export interface MemoryItemListData {
  readonly items: readonly MemoryItem[]
  readonly page: MemoryPage
}

// ── Memory Item Detail ──

/** Full memory item detail. */
export interface MemoryItemDetail {
  readonly id: string
  readonly category: string
  readonly title: string
  readonly summary: string
  readonly tags: string
  readonly type: string
  readonly importance: string
  readonly status: string
  readonly createdAt: string
  readonly updatedAt: string
  readonly recordPreview: string | null
  readonly truncated: boolean
}

// ── Query Parameters ──

/** Parameters for GET /memory/items. */
export interface MemoryItemListParams {
  readonly category?: string
  readonly query?: string
  readonly includeArchived?: boolean
  readonly limit?: number
  readonly offset?: number
}
