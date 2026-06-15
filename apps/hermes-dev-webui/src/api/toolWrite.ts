/**
 * Controlled write tools API client for the Dev WebUI (Phase 2C).
 *
 * Reuses the existing POST /api/dev/v1/tools/dry-run route with
 * body.mode='write_preview' and the existing POST /api/dev/v1/tools/execute
 * route with body.mode='write' — no new route is added.
 *
 * Safety:
 *   - Write execution is dev-sandbox-only and disabled by default. The backend
 *     requires HERMES_TOOL_WRITE_EXECUTION_ENABLED plus the full controlled
 *     chain (preview → confirmation token → argument digest → audit).
 *   - This client never sends an API key, token, or secret other than the
 *     opaque single-use confirmation token issued by the preview response.
 */

import { apiPost } from './client'

import type {
  RollbackExecuteRequest,
  RollbackExecuteResultData,
  RollbackPreviewRequest,
  RollbackPreviewResultData,
  WriteExecuteRequest,
  WriteExecuteResultData,
  WritePreviewRequest,
  WritePreviewResultData,
} from '@/types/api/toolWrite'

const API_PREFIX = '/api/dev/v1'

/**
 * Build a write preview (dry-run). NEVER writes a file. Returns the plan,
 * diff preview, rollback preview, and a single-use confirmation token bound to
 * the plan + argument digest.
 */
export async function runWritePreview(
  request: WritePreviewRequest,
  signal?: AbortSignal,
) {
  return apiPost<WritePreviewResultData>(
    `${API_PREFIX}/tools/dry-run`,
    request,
    undefined,
    signal,
  )
}

/**
 * Execute a controlled write. Requires the writePlanId, confirmation token, and
 * argument digest returned by {@link runWritePreview}. Writes only inside the
 * dev sandbox root; the backend fail-closes on any gate failure.
 */
export async function executeWrite(
  request: WriteExecuteRequest,
  signal?: AbortSignal,
) {
  return apiPost<WriteExecuteResultData>(
    `${API_PREFIX}/tools/execute`,
    request,
    undefined,
    signal,
  )
}

/**
 * Build a rollback preview (dry-run) for a stored rollback manifest. Reuses
 * POST /api/dev/v1/tools/dry-run with body.mode='rollback_preview' — no new
 * route. Loads the manifest, checks the current sandbox state, and returns a
 * rollback-scoped confirmation token. NEVER mutates the filesystem.
 */
export async function runRollbackPreview(
  request: RollbackPreviewRequest,
  signal?: AbortSignal,
) {
  return apiPost<RollbackPreviewResultData>(
    `${API_PREFIX}/tools/dry-run`,
    request,
    undefined,
    signal,
  )
}

/**
 * Execute a controlled rollback. Requires a rollbackId, a rollback-scoped
 * confirmation token, and an argument digest. Reuses
 * POST /api/dev/v1/tools/execute with body.mode='rollback' — no new route.
 */
export async function executeRollback(
  request: RollbackExecuteRequest,
  signal?: AbortSignal,
) {
  return apiPost<RollbackExecuteResultData>(
    `${API_PREFIX}/tools/execute`,
    request,
    undefined,
    signal,
  )
}
