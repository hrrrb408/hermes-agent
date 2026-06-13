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

import type { AuditEventsData, AuditEventsQuery } from '@/types/api/toolAudit'

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
