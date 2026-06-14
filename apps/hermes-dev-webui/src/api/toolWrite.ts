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
