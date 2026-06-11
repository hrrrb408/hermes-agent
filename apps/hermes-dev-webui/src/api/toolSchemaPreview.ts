/**
 * Tool Schema Preview API functions for the Dev WebUI.
 *
 * Provides typed wrappers for the schema preview read-only endpoints:
 * - GET /api/dev/v1/tools/schemas
 * - GET /api/dev/v1/tools/schemas/{canonicalName}
 *
 * Only GET requests. No POST/PUT/PATCH/DELETE. No request body.
 * No Provider headers, no Authorization headers, no tool execution headers.
 * No external URLs. No provider schema sending.
 */

import { apiGet } from './client'

import type {
  ToolSchemaPreviewCatalogData,
  ToolSchemaPreviewLookupData,
} from '@/types/api/toolSchemaPreview'

/** API prefix matching the Dev Web API. */
const API_PREFIX = '/api/dev/v1'

/**
 * Fetch the schema preview catalog for all tools.
 *
 * Returns safe, redacted schema previews for all 71 tools in the policy
 * inventory. No handler, callable, source path, secret, or raw schema
 * is ever exposed.
 */
export async function fetchToolSchemaPreviewCatalog(
  signal?: AbortSignal,
) {
  return apiGet<ToolSchemaPreviewCatalogData>(
    `${API_PREFIX}/tools/schemas`,
    undefined,
    signal,
  )
}

/**
 * Fetch the schema preview for a single tool by canonical name.
 *
 * Exact match only — no fuzzy matching, no case folding, no alias resolution.
 * The canonicalName is URL-encoded to handle special characters safely.
 *
 * @param canonicalName - Exact tool canonical name.
 * @param signal - Optional AbortSignal for request cancellation.
 */
export async function fetchToolSchemaPreviewByCanonicalName(
  canonicalName: string,
  signal?: AbortSignal,
) {
  const encoded = encodeURIComponent(canonicalName)
  return apiGet<ToolSchemaPreviewLookupData>(
    `${API_PREFIX}/tools/schemas/${encoded}`,
    undefined,
    signal,
  )
}
