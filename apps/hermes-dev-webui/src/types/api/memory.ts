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

// ── Memory Writer Dry-Run ──

/** WRITE dry-run request body. */
export interface MemoryWriteDryRunRequest {
  readonly query: string
  readonly candidate: {
    readonly title?: string
    readonly summary: string
    readonly category: string
    readonly type?: string
    readonly importance: 'P0' | 'P1' | 'P2' | 'P3'
    readonly ttl: 'permanent' | 'project' | 'session' | 'temporary'
    readonly tags: readonly string[]
    readonly sourceConfidence?: 'user_confirmed' | 'assistant_inferred'
  }
  readonly options?: {
    readonly allowReviewRecommendation?: boolean
    readonly includeSimilarity?: boolean
    readonly includeEffects?: boolean
  }
}

/** UPDATE dry-run request body. */
export interface MemoryUpdateDryRunRequest {
  readonly candidate: {
    readonly summary: string
    readonly type?: string
    readonly importance?: 'P0' | 'P1' | 'P2' | 'P3'
    readonly ttl?: 'permanent' | 'project' | 'session' | 'temporary'
    readonly tags?: readonly string[]
  }
  readonly options?: {
    readonly includeDiff?: boolean
    readonly includeSimilarity?: boolean
    readonly includeEffects?: boolean
  }
}

/** ARCHIVE dry-run request body. */
export interface MemoryArchiveDryRunRequest {
  readonly reason?: string
  readonly options?: {
    readonly includeEffects?: boolean
    readonly includeReferences?: boolean
  }
}

/** Dry-run target memory info. */
export interface MemoryDryRunTarget {
  readonly memoryId: string
  readonly title: string | null
  readonly category: string
  readonly importance: string
  readonly ttl: string
  readonly status: string
  readonly protected: boolean
  readonly protectionReason: string | null
}

/** Dry-run candidate info. */
export interface MemoryDryRunCandidate {
  readonly titlePreview: string
  readonly summaryPreview: string
  readonly category: string
  readonly type: string
  readonly importance: string
  readonly ttl: string
  readonly tags: readonly string[]
}

/** Dry-run score info. */
export interface MemoryDryRunScore {
  readonly total: number
  readonly breakdown: readonly {
    readonly rule: string
    readonly value: number
  }[]
}

/** Dry-run similarity info. */
export interface MemoryDryRunSimilarity {
  readonly title: number
  readonly summary: number
  readonly combined: number
  readonly overall: number
  readonly tagOverlap: readonly string[]
  readonly coreTagOverlap: readonly string[]
  readonly matchedMemoryId: string | null
  readonly matchedMemoryTitle: string | null
}

/** Dry-run check result. */
export interface MemoryDryRunCheck {
  readonly code: string
  readonly passed: boolean
  readonly message: string
}

/** Dry-run effect prediction. */
export interface MemoryDryRunEffect {
  readonly type: string
  readonly wouldOccur: boolean
  readonly description: string
}

/** Dry-run diff preview (UPDATE only). */
export interface MemoryDryRunDiff {
  readonly titleChanged: boolean
  readonly summaryChanged: boolean
  readonly importanceChanged: boolean
  readonly ttlChanged: boolean
  readonly tagsAdded: readonly string[]
  readonly tagsRemoved: readonly string[]
}

/** Dry-run safety guarantees. */
export interface MemoryDryRunSafety {
  readonly readOnly: boolean
  readonly writeEnabled: boolean
  readonly executeAvailable: boolean
  readonly sideEffects: boolean
}

/** Dry-run config thresholds. */
export interface MemoryDryRunConfig {
  readonly autoWriteEnabled: boolean
  readonly autoUpdateEnabled: boolean
  readonly autoCreateCategories: boolean
  readonly writeThreshold: number
  readonly reviewThreshold: number
  readonly updateSimilarityThreshold: number
  readonly duplicateSimilarityThreshold: number
  readonly candidateSimilarityThreshold: number
}

/** Unified dry-run result data. */
export interface MemoryDryRunResult {
  readonly dryRun: boolean
  readonly operation: 'WRITE' | 'UPDATE' | 'ARCHIVE'
  readonly allowed: boolean
  readonly blockedReason: string | null
  readonly decision: string
  readonly wouldModify: boolean
  readonly wouldEnqueueReview: boolean
  readonly target: MemoryDryRunTarget | null
  readonly candidate: MemoryDryRunCandidate | null
  readonly score?: MemoryDryRunScore
  readonly similarity?: MemoryDryRunSimilarity
  readonly diff?: MemoryDryRunDiff
  readonly checks: readonly MemoryDryRunCheck[]
  readonly effects?: readonly MemoryDryRunEffect[]
  readonly noEffects?: readonly string[]
  readonly safety: MemoryDryRunSafety
  readonly config: MemoryDryRunConfig
  readonly warnings: readonly string[]
}

/** Dry-run operation type for the panel. */
export type MemoryWriterOperation = 'write' | 'update' | 'archive'

/** Loading state for the writer panel. */
export type MemoryWriterLoadingState = 'idle' | 'loading' | 'success' | 'error'
