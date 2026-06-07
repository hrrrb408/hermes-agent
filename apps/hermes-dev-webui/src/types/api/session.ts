/**
 * TypeScript types for the Dev API session endpoints.
 *
 * Matches the frozen OpenAPI contract in docs/webui/openapi/dev-web-api-v1.yaml.
 */

// ── Common ──

/** Pagination metadata. */
export interface SessionPage {
  readonly offset: number
  readonly limit: number
  readonly total: number
  readonly hasMore: boolean
}

// ── Session List ──

/** A single session in the list response. */
export interface SessionListItem {
  readonly id: string
  readonly title: string | null
  readonly source: string
  readonly model: string | null
  readonly messageCount: number
  readonly toolCallCount: number
  readonly archived: boolean
  readonly startedAt: string
  readonly endedAt: string | null
  readonly lastActiveAt: string | null
  readonly preview: string | null
}

/** Response data for GET /sessions. */
export interface SessionListData {
  readonly items: readonly SessionListItem[]
  readonly page: SessionPage
}

// ── Session Detail ──

/** Full session detail. */
export interface SessionDetail {
  readonly id: string
  readonly title: string | null
  readonly source: string
  readonly model: string | null
  readonly messageCount: number
  readonly toolCallCount: number
  readonly inputTokens: number | null
  readonly outputTokens: number | null
  readonly archived: boolean
  readonly startedAt: string
  readonly endedAt: string | null
  readonly lastActiveAt: string | null
  readonly endReason: string | null
}

// ── Query Parameters ──

/** Parameters for GET /sessions. */
export interface SessionListParams {
  readonly limit?: number
  readonly offset?: number
  readonly query?: string
  readonly source?: string
  readonly order?: 'recent' | 'created'
  readonly archived?: 'exclude' | 'include' | 'only'
}

// ── Sort option type ──

export type SessionSortOrder = 'recent' | 'created'
export type SessionArchivedFilter = 'exclude' | 'include' | 'only'
