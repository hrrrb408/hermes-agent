/**
 * TypeScript types for the Dev API review queue endpoints.
 *
 * Phase 1A: read-only GET endpoints.
 * Phase 1B: dry-run POST endpoints (approve/dry-run, reject/dry-run).
 *
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
  readonly dryRunEnabled: true
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

/** Safety flags — read-only with dry-run available in Phase 1B. */
export interface ReviewSafety {
  readonly readOnly: true
  readonly approveAvailable: false
  readonly rejectAvailable: false
  readonly writeAvailable: false
  readonly dryRunAvailable: true
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

// ── Dry-Run Types (Phase 1B) ──

/** Dry-run action type. */
export type DryRunAction = 'APPROVE' | 'REJECT'

/** A single validation check in a dry-run response. */
export interface DryRunCheck {
  readonly code: string
  readonly status: 'pass' | 'fail'
  readonly message: string
}

/** Safety flags for a dry-run response. */
export interface DryRunSafety {
  readonly devOnly: true
  readonly productionBlocked: true
  readonly protectedTarget: boolean
  readonly p0Blocked: boolean
  readonly permanentBlocked: boolean
  readonly duplicateBlocked: boolean
}

/** Target information for a dry-run response. */
export interface DryRunTarget {
  readonly memoryId: string | null
  readonly category: string
  readonly operation: string
}

/** Preview of what would be written/changed. */
export interface DryRunPreview {
  readonly title: string
  readonly summaryPreview: string
  readonly tags: readonly string[]
  readonly reasonPreview: string | null
  readonly redactedPaths: true
}

/** Dry-run result data. */
export interface DryRunResult {
  readonly reviewId: string
  readonly dryRun: true
  readonly action: DryRunAction
  readonly allowed: boolean
  readonly blockedReason: string | null
  readonly wouldModify: boolean
  readonly wouldWriteMemory: boolean
  readonly wouldUpdateReview: boolean
  readonly wouldAppendEvent: boolean
  readonly wouldCreateSnapshot: false
  readonly target: DryRunTarget
  readonly safety: DryRunSafety
  readonly checks: readonly DryRunCheck[]
  readonly preview: DryRunPreview | null
  readonly effects: readonly string[]
  readonly noEffects: readonly string[]
  readonly warnings: readonly string[]
}

/** Request body for POST /reviews/{reviewId}/approve/dry-run. */
export interface ApproveDryRunRequest {
  readonly includeDiff?: boolean
}

/** Request body for POST /reviews/{reviewId}/reject/dry-run. */
export interface RejectDryRunRequest {
  readonly reason?: string
  readonly includeDiff?: boolean
}
