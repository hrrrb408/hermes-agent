/**
 * TypeScript types for the Dev API context preview endpoint.
 *
 * Matches the Phase 0C-05 API contract.
 */

/** A matched category in context preview results. */
export interface ContextMatchedCategory {
  readonly key: string
  readonly title: string
  readonly score: number
  readonly priority: string
}

/** A matched memory in context preview results. */
export interface ContextMatchedMemory {
  readonly id: string
  readonly category: string
  readonly title: string
  readonly summary: string
  readonly score: number
  readonly truncated: boolean
}

/** Context preview limits applied. */
export interface ContextPreviewLimits {
  readonly maxCategories: number
  readonly maxMemories: number
  readonly maxRecordChars: number
}

/** Response data for POST /context/preview. */
export interface ContextPreviewData {
  readonly query: string
  readonly matchedCategories: readonly ContextMatchedCategory[]
  readonly memories: readonly ContextMatchedMemory[]
  readonly limits: ContextPreviewLimits
  readonly sideEffects: boolean
}

/** Request body for POST /context/preview. */
export interface ContextPreviewRequest {
  readonly query: string
  readonly options?: {
    readonly maxCategories?: number
    readonly maxMemories?: number
    readonly maxRecordChars?: number
    readonly includeArchived?: boolean
    readonly showScores?: boolean
  }
}
