/**
 * TypeScript types for the Dev API review queue endpoints.
 *
 * Matches the Phase 1A API contract. All fields are read-only.
 * No fingerprint, source, raw candidate, or evaluation details
 * are included — those are forbidden fields.
 */

// ── Review Status ──

/** Review queue status response data. */
export interface ReviewQueueStatus {
  readonly available: boolean
  readonly readOnly: true
  readonly queueEnabled: false
  readonly writeEnabled: false
  readonly approveEnabled: false
  readonly rejectEnabled: false
  readonly enqueueEnabled: false
  readonly counts: {
    readonly pending: number
    readonly approved: number
    readonly rejected: number
    readonly failed: number
    readonly total: number
  }
  readonly storage: {
    readonly available: boolean
    readonly redactedPath: string
  }
}

// ── Review List Item ──

/** A single review item in list responses. */
export interface ReviewListItem {
  readonly reviewId: string
  readonly status: 'pending' | 'approved' | 'rejected' | 'failed'
  readonly decision: string
  readonly proposedAction: string
  readonly category: string
  readonly title: string
  readonly summaryPreview: string
  readonly tags: readonly string[]
  readonly score: number
  readonly reasonCodes: readonly string[]
  readonly targetMemoryId: string | null
  readonly protectedTarget: boolean
  readonly occurrenceCount: number
  readonly createdAt: string
  readonly updatedAt: string
}

/** Pagination metadata for review items. */
export interface ReviewPage {
  readonly limit: number
  readonly offset: number
  readonly total: number
  readonly hasMore: boolean
}

/** Response data for GET /reviews. */
export interface ReviewListData {
  readonly items: readonly ReviewListItem[]
  readonly page: ReviewPage
}

// ── Review Detail ──

/** Score breakdown entry. */
export interface ScoreBreakdownEntry {
  readonly rule: string
  readonly value: number
}

/** Similarity scores. */
export interface SimilarityScores {
  readonly title: number
  readonly summary: number
  readonly combined: number
  readonly overall: number
}

/** Review target information. */
export interface ReviewTarget {
  readonly memoryId: string | null
  readonly title: string | null
  readonly category: string | null
  readonly protected: boolean
}

/** Review timestamps. */
export interface ReviewTimestamps {
  readonly createdAt: string
  readonly updatedAt: string
  readonly lastSeenAt: string
  readonly reviewedAt: string | null
}

/** Review error info. */
export interface ReviewErrors {
  readonly lastError: string | null
}

/** Safety flags — always read-only in Phase 1A. */
export interface ReviewSafety {
  readonly readOnly: true
  readonly approveAvailable: false
  readonly rejectAvailable: false
  readonly writeAvailable: false
  readonly dryRunAvailable: false
}

/** Full review item detail. */
export interface ReviewDetail extends ReviewListItem {
  readonly summary: string
  readonly scoreBreakdown: readonly ScoreBreakdownEntry[]
  readonly similarity: SimilarityScores
  readonly target: ReviewTarget
  readonly timestamps: ReviewTimestamps
  readonly errors: ReviewErrors
  readonly safety: ReviewSafety
}

// ── Query Parameters ──

/** Status filter values. */
export type ReviewStatusFilter = 'pending' | 'approved' | 'rejected' | 'failed' | 'all'

/** Decision filter values. */
export type ReviewDecisionFilter =
  | 'WRITE'
  | 'UPDATE'
  | 'REVIEW'
  | 'SKIP'
  | 'SKIP_DUPLICATE'
  | 'UNDECIDED'
  | 'all'

/** Sort order for review list. */
export type ReviewOrder = 'created_desc' | 'updated_desc'

/** Parameters for GET /reviews. */
export interface ReviewListParams {
  readonly status?: ReviewStatusFilter
  readonly decision?: ReviewDecisionFilter
  readonly category?: string
  readonly query?: string
  readonly limit?: number
  readonly offset?: number
  readonly order?: ReviewOrder
}
