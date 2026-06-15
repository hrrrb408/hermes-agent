/**
 * Type definitions for the read-only Tool Audit Events API.
 *
 * These types model the safe, redacted audit event items returned by
 * GET /api/dev/v1/tools/audit-events. Raw confirmation tokens, full token
 * hashes, raw arguments, secrets, callable objects, function reprs, and
 * provider payloads are never present in these shapes.
 */

/** Audit kind selector. */
export type AuditKind = 'dry_run' | 'pre_execution' | 'post_execution'

/**
 * Phase 2D: the full durable-store audit kind set, including provider /
 * rollback / confirmation / internal / write kinds served by the store query
 * engine. Legacy UI still uses the narrow {@link AuditKind} union.
 */
export type StoreAuditKind =
  | 'dry_run'
  | 'pre_execution'
  | 'post_execution'
  | 'write'
  | 'provider'
  | 'rollback'
  | 'confirmation'
  | 'internal'

/** Side-effect flags surfaced from a post-execution audit event. */
export interface AuditSideEffects {
  readonly providerSchemaSent: boolean
  readonly providerApiCalled: boolean
  readonly externalSideEffects: boolean
}

/** A single safe, redacted audit event item. */
export interface AuditEventItem {
  readonly auditKind: AuditKind
  readonly auditId: string | null
  readonly timestamp: string | null
  readonly canonicalName: string | null
  readonly decision?: string | null
  readonly riskTier?: string | null
  readonly toolExists?: boolean | null
  readonly dryRunDecisionDigest?: string | null
  readonly executeRequestId?: string | null
  readonly dryRunRequestId?: string | null
  readonly preExecutionAuditId?: string | null
  readonly handlerLookupId?: string | null
  readonly dispatchId?: string | null
  readonly handlerCallId?: string | null
  readonly executionStatus?: string | null
  readonly handlerCallStatus?: string | null
  readonly sideEffects?: AuditSideEffects
  readonly safeSummary?: Record<string, unknown>
}

/** Response data for the audit events endpoint. */
export interface AuditEventsData {
  readonly auditKind: AuditKind
  readonly items: readonly AuditEventItem[]
  readonly nextCursor: string | null
  readonly limit: number
  readonly hasMore: boolean
  readonly skippedMalformed: number
}

/** Query parameters for the audit events endpoint. */
export interface AuditEventsQuery {
  readonly auditKind: AuditKind
  readonly limit?: number
  readonly cursor?: string
  readonly canonicalName?: string
}

// ---------------------------------------------------------------------------
// Phase 2D — durable-store query types
// ---------------------------------------------------------------------------

/** A single safe canonical audit event item from the durable store. */
export interface StoreAuditEventItem {
  readonly eventId: string | null
  readonly sequence: number | null
  readonly createdAt: string | null
  readonly eventType: string | null
  readonly auditKind: StoreAuditKind | string | null
  readonly source?: string | null
  readonly toolId?: string | null
  readonly status?: string | null
  readonly blockedReason?: string | null
  readonly readOnly?: boolean | null
  readonly writeRequired?: boolean | null
  readonly providerMode?: string | null
  readonly providerSchemaSent?: boolean | null
  readonly providerApiCalled?: boolean | null
  readonly externalNetworkCalled?: boolean | null
  readonly localSideEffects?: boolean | null
  readonly externalSideEffects?: boolean | null
  readonly redactionApplied?: boolean | null
  readonly executionId?: string | null
  readonly dryRunId?: string | null
  readonly dispatchId?: string | null
  readonly handlerCallId?: string | null
  readonly preExecutionAuditId?: string | null
  readonly postExecutionAuditId?: string | null
  readonly providerRequestId?: string | null
  readonly providerResponseId?: string | null
  readonly writePlanId?: string | null
  readonly writePreviewId?: string | null
  readonly rollbackId?: string | null
  readonly confirmationTokenId?: string | null
  readonly summary?: Record<string, unknown>
  readonly safeMetadata?: Record<string, unknown>
  readonly schemaVersion?: string | null
}

/** Store health summary surfaced alongside query results. */
export interface AuditStoreStatus {
  readonly present: boolean
  readonly segmentCount: number
  readonly monotonic: boolean
  readonly activeSegment: string | null
  readonly schemaVersion: string
}

/** Index health summary surfaced alongside query results. */
export interface AuditIndexStatus {
  readonly present: boolean
  readonly consistent: boolean
  readonly stale: boolean
  readonly lastSequence: number
  readonly eventCount: number
  readonly segmentCount: number
  readonly fields: readonly string[]
}

/** Response data for the Phase 2D durable-store audit query. */
export interface StoreAuditEventsData {
  readonly items: readonly StoreAuditEventItem[]
  readonly nextCursor: string | null
  readonly previousCursor: string | null
  readonly hasMore: boolean
  readonly limit: number
  readonly order: 'asc' | 'desc'
  readonly query: Record<string, unknown>
  readonly storeStatus: AuditStoreStatus
  readonly indexStatus: AuditIndexStatus
  readonly schemaVersion: string
  readonly skippedMalformed: number
}

/** Query parameters for the Phase 2D durable-store audit query. */
export interface StoreAuditEventsQuery {
  readonly auditKind: StoreAuditKind | string
  readonly limit?: number
  readonly cursor?: string
  readonly order?: 'asc' | 'desc'
  readonly eventType?: string
  readonly toolId?: string
  readonly status?: string
  readonly source?: string
  readonly providerMode?: string
  readonly readOnly?: boolean
  readonly writeRequired?: boolean
  readonly fromCreatedAt?: string
  readonly toCreatedAt?: string
  readonly search?: string
  readonly includeSummary?: boolean
}
