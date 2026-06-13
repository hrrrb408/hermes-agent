/**
 * Tool Dry-Run + Tool Execute API functions for the Dev WebUI.
 *
 * Provides typed wrappers for the controlled execution endpoints:
 * - POST /api/dev/v1/tools/dry-run  (non-mutating policy decision)
 * - POST /api/dev/v1/tools/execute  (controlled execution gate)
 *
 * Safety:
 *   - The raw confirmation token returned by dry-run is kept in memory by
 *     the caller (the Pinia store) and passed straight through to execute.
 *     It is never logged here, never persisted to storage.
 *   - No raw arguments are written to persistent storage by this module.
 *   - No Provider configuration is ever sent.
 */

import { apiPost } from './client'

import type {
  DryRunRequest,
  DryRunResultData,
  ExecuteRequest,
  ExecuteResultData,
} from '@/types/api/toolExecute'

/** API prefix matching the Dev Web API. */
const API_PREFIX = '/api/dev/v1'

/**
 * Evaluate the dry-run policy for a proposed tool call.
 *
 * Non-mutating: no tool handler is called, no provider schema is sent.
 * When ``issueConfirmationToken`` is true and the tool is eligible, the
 * response includes a one-time confirmation token (in-memory only).
 */
export async function runDryRun(
  request: DryRunRequest,
  signal?: AbortSignal,
) {
  return apiPost<DryRunResultData>(
    `${API_PREFIX}/tools/dry-run`,
    request,
    undefined,
    signal,
  )
}

/**
 * Evaluate a controlled tool execution request through the full gate stack.
 *
 * The raw confirmation token is passed straight through from the prior
 * dry-run response — never logged, never persisted.
 */
export async function executeTool(
  request: ExecuteRequest,
  signal?: AbortSignal,
) {
  return apiPost<ExecuteResultData>(
    `${API_PREFIX}/tools/execute`,
    request,
    undefined,
    signal,
  )
}
