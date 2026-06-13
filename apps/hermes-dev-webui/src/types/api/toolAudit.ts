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
