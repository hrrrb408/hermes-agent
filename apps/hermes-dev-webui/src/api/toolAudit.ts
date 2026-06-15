/**
 * Tool Audit Events API functions for the Dev WebUI.
 *
 * Provides a typed wrapper for the read-only audit events endpoint:
 * - GET /api/dev/v1/tools/audit-events
 *
 * Only GET requests. No POST/PUT/PATCH/DELETE. No request body.
 * No Provider headers, no Authorization headers. The response contains
 * only safe, redacted audit event items.
 */

import { apiGet } from './client'

import type {
  AuditEventsData,
  AuditEventsQuery,
  StoreAuditEventsData,
  StoreAuditEventsQuery,
} from '@/types/api/toolAudit'

/** API prefix matching the Dev Web API. */
const API_PREFIX = '/api/dev/v1'

/** Build a query string from audit events query parameters. */
function buildAuditQueryString(query: AuditEventsQuery): string {
  const searchParams = new URLSearchParams()
  searchParams.set('auditKind', query.auditKind)
  if (query.limit !== undefined) {
    searchParams.set('limit', String(query.limit))
  }
  if (query.cursor !== undefined && query.cursor !== '') {
    searchParams.set('cursor', query.cursor)
  }
  if (query.canonicalName !== undefined && query.canonicalName !== '') {
    searchParams.set('canonicalName', query.canonicalName)
  }
  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

/**
 * Fetch safe, redacted audit events for a given audit kind.
 *
 * Returns dry-run, pre-execution, or post-execution audit events. A
 * missing audit file returns an empty item list. Malformed lines are
 * skipped safely. No raw token, full token hash, raw arguments, or
 * secrets are ever exposed.
 */
export async function getAuditEvents(
  query: AuditEventsQuery,
  signal?: AbortSignal,
) {
  const qs = buildAuditQueryString(query)
  return apiGet<AuditEventsData>(
    `${API_PREFIX}/tools/audit-events${qs}`,
    undefined,
    signal,
  )
}

/**
 * Phase 2D: build a query string from durable-store query parameters.
 *
 * Any provided filter selects the store query path server-side.
 */
function buildStoreAuditQueryString(query: StoreAuditEventsQuery): string {
  const sp = new URLSearchParams()
  sp.set('auditKind', query.auditKind)
  if (query.limit !== undefined) sp.set('limit', String(query.limit))
  if (query.cursor) sp.set('cursor', query.cursor)
  if (query.order) sp.set('order', query.order)
  if (query.eventType) sp.set('eventType', query.eventType)
  if (query.toolId) sp.set('toolId', query.toolId)
  if (query.status) sp.set('status', query.status)
  if (query.source) sp.set('source', query.source)
  if (query.providerMode) sp.set('providerMode', query.providerMode)
  if (query.readOnly !== undefined) sp.set('readOnly', String(query.readOnly))
  if (query.writeRequired !== undefined) sp.set('writeRequired', String(query.writeRequired))
  if (query.fromCreatedAt) sp.set('fromCreatedAt', query.fromCreatedAt)
  if (query.toCreatedAt) sp.set('toCreatedAt', query.toCreatedAt)
  if (query.search) sp.set('search', query.search)
  if (query.includeSummary !== undefined) sp.set('includeSummary', String(query.includeSummary))
  const qs = sp.toString()
  return qs ? `?${qs}` : ''
}

/**
 * Phase 2D: fetch safe, redacted audit events from the durable audit store.
 *
 * Supports cursor pagination, filters, safe search, and store/index status.
 * The response carries only sanitized, JSON-native items — no raw token, full
 * token hash, raw arguments, secrets, callable reprs, or production paths.
 */
export async function getAuditEventsV2(
  query: StoreAuditEventsQuery,
  signal?: AbortSignal,
) {
  const qs = buildStoreAuditQueryString(query)
  return apiGet<StoreAuditEventsData>(
    `${API_PREFIX}/tools/audit-events${qs}`,
    undefined,
    signal,
  )
}
